"""Data extractors for populating system databases from imported files."""
import os
import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from db_manager import execute, query

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger("engine.extractors")


class RelationshipExtractor:
    """Extract relationship data from People markdown files."""
    
    def __init__(self):
        self.relationships_dir = PROJECT_ROOT / "self" / "relationships"
    
    def extract_all(self):
        """Extract all relationships from People files."""
        count = 0
        for file_path in self.relationships_dir.glob("*.md"):
            if file_path.name == "People.base":
                continue
            
            data = self._parse_file(file_path)
            if data:
                count += self._insert_relationship(data)
        
        return count
    
    def _parse_file(self, file_path: Path) -> dict:
        """Parse a markdown People file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    metadata = yaml.safe_load(parts[1]) or {}
                    return metadata
        except Exception as e:
            print(f"Error parsing {file_path.name}: {e}")
        
        return {}
    
    def _insert_relationship(self, data: dict) -> int:
        """Insert relationship into database."""
        try:
            name = data.get("Name", "Unknown")
            email = data.get("email", "")
            phone = data.get("number", "")
            cpf = data.get("CPF", "")
            birth_date = data.get("Birth Date", "")
            
            execute("self", """
                INSERT OR REPLACE INTO relationships 
                (name, email, phone, cpf, birth_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, email, phone, cpf, birth_date, datetime.now().isoformat()))
            
            return 1
        except Exception as e:
            print(f"Error inserting relationship {data.get('Name')}: {e}")
            return 0


class GoalExtractor:
    """Extract goals and projects from Life Plans files."""
    
    def __init__(self):
        self.goals_dir = PROJECT_ROOT / "self" / "goals"
    
    def extract_all(self):
        """Extract all goals from Life Plans files."""
        count = 0
        for file_path in self.goals_dir.glob("*.md"):
            data = self._parse_file(file_path)
            if data:
                count += self._insert_goal(file_path.name, data)
        
        return count
    
    def _parse_file(self, file_path: Path) -> dict:
        """Parse a markdown goal/plan file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {}
            text_content = content
            
            # Extract frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1]) or {}
                    text_content = parts[2]
            
            # Extract title and key phrases
            metadata['content'] = text_content[:500]  # Store first 500 chars
            metadata['content_length'] = len(text_content)
            
            return metadata
        except Exception as e:
            print(f"Error parsing {file_path.name}: {e}")
        
        return {}
    
    def _insert_goal(self, filename: str, data: dict) -> int:
        """Insert goal into database."""
        try:
            title = data.get('title') or data.get('Title') or filename.replace('.md', '')
            description = data.get('content', '')
            category = data.get('category') or (data.get('tags', ['goal'])[0] if data.get('tags') else 'goal')
            status = data.get('status', 'active')
            
            execute("self", """
                INSERT OR REPLACE INTO goals 
                (title, description, category, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (title, description, category, status, datetime.now().isoformat()))
            
            return 1
        except Exception as e:
            print(f"Error inserting goal {filename}: {e}")
            return 0


class DailyNoteExtractor:
    """Extract insights, behaviors, and habits from Daily Notes."""
    
    def __init__(self):
        self.inbox_dir = PROJECT_ROOT / "command" / "inbox"
    
    def extract_all(self):
        """Extract all insights from daily notes."""
        count = 0
        for file_path in self.inbox_dir.glob("*.md"):
            data = self._parse_file(file_path)
            if data:
                count += self._insert_insights(file_path.name, data)
        
        return count
    
    def _parse_file(self, file_path: Path) -> dict:
        """Parse a daily note file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {}
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1]) or {}
                    metadata['content'] = parts[2]
            else:
                metadata['content'] = content
            
            return metadata
        except Exception as e:
            print(f"Error parsing {file_path.name}: {e}")
        
        return {}
    
    def _insert_insights(self, filename: str, data: dict) -> int:
        """Insert insights and behaviors."""
        count = 0
        try:
            content = data.get('content', '')
            
            # Extract mood/emotion patterns
            emotions = self._extract_emotions(content)
            for emotion in emotions:
                try:
                    execute("self", """
                        INSERT INTO behaviors 
                        (behavior_type, response, observed_date, frequency)
                        VALUES (?, ?, ?, ?)
                    """, ('emotion', emotion, datetime.now().isoformat(), 1))
                    count += 1
                except Exception as e:
                    logger.debug("Failed to insert emotion behavior: %s", e)
            
            # Extract activity patterns
            activities = self._extract_activities(content)
            for activity in activities:
                try:
                    execute("self", """
                        INSERT INTO behaviors 
                        (behavior_type, response, observed_date, frequency)
                        VALUES (?, ?, ?, ?)
                    """, ('activity', activity, datetime.now().isoformat(), 1))
                    count += 1
                except Exception as e:
                    logger.debug("Failed to insert activity behavior: %s", e)
        except Exception as e:
            print(f"Error inserting insights from {filename}: {e}")
        
        return count
    
    def _extract_emotions(self, content: str) -> list:
        """Extract emotion keywords."""
        emotions = []
        patterns = [
            r'feel(?:ing)?[\s:]+([a-z]+)',
            r'(?:felt|feeling|felt)\s+([a-z]+)',
            r'(?:happy|sad|angry|anxious|stressed|excited|motivated|tired)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content.lower())
            emotions.extend(matches)
        
        return list(set(emotions))[:5]  # Limit to 5 unique
    
    def _extract_activities(self, content: str) -> list:
        """Extract activity keywords."""
        activities = []
        patterns = [
            r'(?:did|doing|studied|worked|exercised|read|wrote)\s+([a-z\s]+)',
            r'(?:studied|work|exercise|read|write|coding|design)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content.lower())
            activities.extend(matches)
        
        return list(set(activities))[:5]  # Limit to 5 unique


class FinanceExtractor:
    """Extract financial and professional information."""
    
    def __init__(self):
        self.finances_dir = PROJECT_ROOT / "command" / "finances"
    
    def extract_all(self):
        """Extract all financial information."""
        count = 0
        for file_path in self.finances_dir.glob("*.md"):
            data = self._parse_file(file_path)
            if data:
                count += self._insert_finance_data(file_path.name, data)
        
        return count
    
    def _parse_file(self, file_path: Path) -> dict:
        """Parse a finance/professional file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {}
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1]) or {}
                    metadata['content'] = parts[2]
            else:
                metadata['content'] = content
            
            return metadata
        except Exception as e:
            print(f"Error parsing {file_path.name}: {e}")
        
        return {}
    
    def _insert_finance_data(self, filename: str, data: dict) -> int:
        """Insert finance-related data."""
        count = 0
        try:
            content = data.get('content', '')
            
            # Extract job titles/roles
            roles = self._extract_roles(content)
            for role in roles:
                try:
                    execute("self", """
                        INSERT INTO traits 
                        (trait_name, trait_category, description)
                        VALUES (?, ?, ?)
                    """, ('professional_role', role, filename))
                    count += 1
                except Exception as e:
                    logger.debug("Failed to insert role trait: %s", e)
            
            # Extract skills
            skills = self._extract_skills(content)
            for skill in skills:
                try:
                    execute("self", """
                        INSERT INTO traits 
                        (trait_name, trait_category, description)
                        VALUES (?, ?, ?)
                    """, ('skill', skill, filename))
                    count += 1
                except Exception as e:
                    logger.debug("Failed to insert skill trait: %s", e)
        except Exception as e:
            print(f"Error inserting finance data from {filename}: {e}")
        
        return count
    
    def _extract_roles(self, content: str) -> list:
        """Extract job roles."""
        roles = []
        patterns = [
            r'(?:Manager|Developer|Engineer|Consultant|Analyst|Coordinator)',
            r'(?:Health|Public Health|Program Manager)',
            r'(?:Senior|Junior|Lead|Principal)\s+([A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            roles.extend(matches)
        
        return list(set(roles))[:10]
    
    def _extract_skills(self, content: str) -> list:
        """Extract skills and competencies."""
        skills = []
        keywords = [
            'Python', 'JavaScript', 'SQL', 'Data Analysis', 'Project Management',
            'Communication', 'Leadership', 'Research', 'Writing', 'Strategy',
            'Negotiation', 'Problem Solving', 'Public Health', 'AI', 'Machine Learning'
        ]
        
        for keyword in keywords:
            if keyword.lower() in content.lower():
                skills.append(keyword)
        
        return list(set(skills))[:15]


class ProfileExtractor:
    """Extract and update profile information."""
    
    def __init__(self):
        self.profile_dir = PROJECT_ROOT / "self" / "profile"
    
    def extract_all(self):
        """Extract profile information."""
        count = 0
        
        # Check for profile file
        for file_path in self.profile_dir.glob("*.md"):
            data = self._parse_file(file_path)
            if data:
                count += self._update_profile(data)
        
        return count
    
    def _parse_file(self, file_path: Path) -> dict:
        """Parse profile file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {}
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1]) or {}
                    metadata['content'] = parts[2]
            else:
                metadata['content'] = content
            
            return metadata
        except Exception as e:
            print(f"Error parsing profile file: {e}")
        
        return {}
    
    def _update_profile(self, data: dict) -> int:
        """Update profile in database."""
        try:
            content = data.get('content', '')
            
            # Extract key traits and descriptions
            description = content[:1000]
            writing_style = data.get('writing_style', 'analytical')
            
            execute("self", """
                UPDATE profile 
                SET description = ?, updated_at = ?
                WHERE id = 1
            """, (description, datetime.now().isoformat()))
            
            return 1
        except Exception as e:
            print(f"Error updating profile: {e}")
        
        return 0


def run_all_extractors():
    """Run all extractors and populate databases."""
    print("🔍 Starting Data Extraction Pipeline")
    print("=" * 60)
    
    results = {}
    
    # Extract relationships
    print("\n📍 Extracting Relationships...")
    re = RelationshipExtractor()
    count = re.extract_all()
    results['relationships'] = count
    print(f"   ✓ Extracted {count} relationships")
    
    # Extract goals
    print("\n🎯 Extracting Goals...")
    ge = GoalExtractor()
    count = ge.extract_all()
    results['goals'] = count
    print(f"   ✓ Extracted {count} goals/plans")
    
    # Extract daily notes
    print("\n📔 Extracting Daily Notes...")
    dne = DailyNoteExtractor()
    count = dne.extract_all()
    results['daily_insights'] = count
    print(f"   ✓ Extracted {count} insights/behaviors")
    
    # Extract finance data
    print("\n💰 Extracting Finance/Professional Data...")
    fe = FinanceExtractor()
    count = fe.extract_all()
    results['finance_traits'] = count
    print(f"   ✓ Extracted {count} professional traits")
    
    # Extract profile
    print("\n👤 Extracting Profile...")
    pe = ProfileExtractor()
    count = pe.extract_all()
    results['profile_updates'] = count
    print(f"   ✓ Updated profile")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 60)
    total = sum(results.values())
    for key, count in results.items():
        print(f"   {key:20} {count:4} records")
    print(f"\n   {'TOTAL':20} {total:4} records extracted")
    
    return results


if __name__ == "__main__":
    run_all_extractors()
