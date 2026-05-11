---
title: 📓 Daily Notes Dashboard
type: daily-note
tags:
- 0ea5e9
- 0ea5e933
- 10b981
- 10b98133
- command
- f59e0b
- f59e0b33
- fff
- inbox
created: 2025-12-05T19:35
updated: 2025-12-07T17:44
---

# 📓 Daily Notes Dashboard

---

## 📊 DAILY NOTES SNAPSHOT

### Key Metrics at a Glance
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"');
const pagesWithMood = pages.filter(p => p.mood);
const pagesWithTopics = pages.filter(p => p.topics);
const pagesWithTags = pages.filter(p => p.file.tags && p.file.tags.length > 0);

let totalMoods = 0;
let totalTopics = 0;
let totalTags = 0;
let uniqueMoods = new Set();
let uniqueTopics = new Set();
let uniqueTags = new Set();

pagesWithMood.forEach(p => {
  if (p.mood && Array.isArray(p.mood)) {
    totalMoods += p.mood.length;
    p.mood.forEach(m => uniqueMoods.add(m));
  }
});

pagesWithTopics.forEach(p => {
  if (p.topics && Array.isArray(p.topics)) {
    totalTopics += p.topics.length;
    p.topics.forEach(t => uniqueTopics.add(t));
  }
});

pagesWithTags.forEach(p => {
  if (p.file.tags && Array.isArray(p.file.tags)) {
    totalTags += p.file.tags.length;
    p.file.tags.forEach(t => uniqueTags.add(t));
  }
});

dv.paragraph(`
---

### 💭 MOOD TRACKING

| 📝 Total Notes | 😊 Notes with Mood | 😢 Unique Moods | 📊 Total Mood Entries |
|:---:|:---:|:---:|:---:|
| **${pages.length}** | **${pagesWithMood.length}** | **${uniqueMoods.size}** | **${totalMoods}** |

### 🎯 TOPICS & TAGS

| 🎯 Notes with Topics | 📚 Unique Topics | 🏷️ Notes with Tags | 🔖 Unique Tags |
|:---:|:---:|:---:|:---:|
| **${pagesWithTopics.length}** | **${uniqueTopics.size}** | **${pagesWithTags.length}** | **${uniqueTags.size}** |

### 📈 SUMMARY

| 📋 Total Entries | 💭 Avg Moods/Note | 🎯 Avg Topics/Note | 🏷️ Avg Tags/Note |
|:---:|:---:|:---:|:---:|
| **${pages.length}** | **${(totalMoods/pagesWithMood.length).toFixed(1)}** | **${(totalTopics/pagesWithTopics.length).toFixed(1)}** | **${(totalTags/pagesWithTags.length).toFixed(1)}** |

---
`);
```

---

## 📅 DAILY NOTES HEATMAP TRACKER

### 2025 Daily Notes Contribution Heatmap (Heatmap Tracker Plugin)

```dataviewjs
const trackerData = {
    year: 2025,
    entries: [],
    heatmapTitle: "📅 <b>2025 Daily Notes Activity Heatmap</b>",
    heatmapSubtitle: "Track your daily journaling consistency throughout the year. Green intensity shows your note creation activity.",
    separateMonths: true,
    showCurrentDayBorder: true,
    defaultEntryIntensity: 1
}

// Get all pages from Daily Notes folder and subfolders using wildcard path
const allPages = dv.pages('"PERSONAL/Daily Notes"') || [];

for(let page of allPages){
    let dateStr = null;
    let parseMethod = '';
    
    // Skip dashboard file
    if(page.file.name === 'Daily Notes Dashboard.md') {
        continue;
    }
    
    // Try created property first (most reliable)
    if(page.created) {
        const createdDate = new Date(page.created);
        if(!isNaN(createdDate)) {
            dateStr = createdDate.toISOString().split('T')[0];
            parseMethod = 'created property';
        }
    }
    
    // If still no date, fallback to filename parsing
    if(!dateStr && page.file && page.file.name) {
        const fileName = page.file.name.replace('.md', '').trim();
        
        // Format 1: YYYY-MM-DD (e.g., "2025-01-03")
        let match = fileName.match(/(\d{4})-(\d{2})-(\d{2})/);
        if(match) {
            dateStr = `${match[1]}-${match[2]}-${match[3]}`;
            parseMethod = 'filename format 1 (YYYY-MM-DD)';
        }
        
        // Format 2: DD Mon YYYY (e.g., "27 Nov 2025")
        if(!dateStr) {
            match = fileName.match(/(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})/i);
            if(match) {
                const day = match[1].padStart(2, '0');
                const monthStr = match[2];
                const year = match[3];
                
                const monthMap = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                };
                
                const month = monthMap[monthStr];
                if(month) {
                    dateStr = `${year}-${month}-${day}`;
                    parseMethod = 'filename format 2 (DD Mon YYYY)';
                }
            }
        }
        
        // Format 3: MMM DD, YYYY (e.g., "Dec 06, 2025")
        if(!dateStr) {
            match = fileName.match(/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})/i);
            if(match) {
                const monthStr = match[1];
                const day = match[2].padStart(2, '0');
                const year = match[3];
                
                const monthMap = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                };
                
                const month = monthMap[monthStr];
                if(month) {
                    dateStr = `${year}-${month}-${day}`;
                    parseMethod = 'filename format 3 (MMM DD, YYYY)';
                }
            }
        }
    }
    
    if(dateStr) {
        trackerData.entries.push({
            date: dateStr,
            filePath: page.file.path,
            intensity: 1
        })
    }
}


trackerData.basePath = 'PERSONAL/Daily Notes';

renderHeatmapTracker(this.container, trackerData)
```


---

---

## 🎯 MOOD ANALYSIS

### 🏆 Top 15 Moods (Most Frequent)
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"').where(p => p.mood);
const moods = {};

pages.forEach(page => {
  if (page.mood && Array.isArray(page.mood)) {
    page.mood.forEach(mood => {
      moods[mood] = (moods[mood] || 0) + 1;
    });
  }
});

const sorted = Object.entries(moods)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 15);

let chart = {
  type: 'bar',
  data: {
    labels: sorted.map(s => s[0]),
    datasets: [
      {
        label: 'Frequency',
        data: sorted.map(s => s[1]),
        borderColor: '#0ea5e9',
        backgroundColor: '#0ea5e933',
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }
    ]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: { ticks: { font: { size: 11 } } },
      y: { ticks: { font: { size: 11 } } }
    }
  }
};

window.renderChart(chart, this.container);
```

### 🔴 Mood Distribution (Pie Chart)
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"').where(p => p.mood);
const moods = {};

pages.forEach(page => {
  if (page.mood && Array.isArray(page.mood)) {
    page.mood.forEach(mood => {
      moods[mood] = (moods[mood] || 0) + 1;
    });
  }
});

const sorted = Object.entries(moods)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 10);

const labels = sorted.map(([mood]) => mood);
const data = sorted.map(([, count]) => count);

if (labels.length > 0) {
  const chartData = {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        label: 'Frequency',
        data: data,
        backgroundColor: [
          'rgba(255, 99, 132, 0.8)',
          'rgba(54, 162, 235, 0.8)',
          'rgba(255, 206, 86, 0.8)',
          'rgba(75, 192, 192, 0.8)',
          'rgba(153, 102, 255, 0.8)',
          'rgba(255, 159, 64, 0.8)',
          'rgba(199, 199, 199, 0.8)',
          'rgba(83, 102, 255, 0.8)',
          'rgba(255, 99, 200, 0.8)',
          'rgba(100, 200, 100, 0.8)'
        ],
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        title: {
          display: true,
          text: '😊 Top 10 Moods Distribution',
          font: { size: 16, weight: 'bold' }
        },
        legend: { 
          display: true, 
          position: 'right',
          labels: {
            font: { size: 11 },
            padding: 15
          }
        }
      }
    }
  };
  
  window.renderChart(chartData, this.container);
}
```

---

## 📚 TOPICS ANALYSIS

### 🏆 Top 12 Topics
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"');
const topics = {};

pages.forEach(page => {
  if (page.topics && Array.isArray(page.topics)) {
    page.topics.forEach(topic => {
      topics[topic] = (topics[topic] || 0) + 1;
    });
  }
});

const sorted = Object.entries(topics)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 12);

let chart = {
  type: 'bar',
  data: {
    labels: sorted.map(s => s[0]),
    datasets: [
      {
        label: 'Count',
        data: sorted.map(s => s[1]),
        borderColor: '#10b981',
        backgroundColor: '#10b98133',
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }
    ]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: { ticks: { font: { size: 11 } } },
      y: { ticks: { font: { size: 11 } } }
    }
  }
};

window.renderChart(chart, this.container);
```

---

## 🏷️ TAGS ANALYSIS

### 🏆 Top 12 Tags (Frontmatter + Inline)
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"');
const tags = {};

pages.forEach(page => {
  if (page.file.tags && Array.isArray(page.file.tags)) {
    page.file.tags.forEach(tag => {
      tags[tag] = (tags[tag] || 0) + 1;
    });
  }
});

const sorted = Object.entries(tags)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 12);

const allTagsCount = Object.keys(tags).length;

dv.paragraph(`🏷️ Showing top 12 of ${allTagsCount} total tags (frontmatter + inline)\n`);

dv.paragraph(`
| Tag | Count | % |
|:---|---:|---:|
${sorted.map(([tag, count]) => 
  `| **${tag}** | ${count} | ${((count/Object.values(tags).reduce((a,b) => a+b, 0))*100).toFixed(1)}% |`
).join('\n')}
`);

if (sorted.length > 0) {
  const labels = sorted.map(([tag]) => tag);
  const data = sorted.map(([, count]) => count);

  const chartData = {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Frequency',
        data: data,
        backgroundColor: 'rgba(75, 159, 192, 0.8)',
        borderColor: 'rgba(75, 159, 192, 1)',
        borderWidth: 2,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      indexAxis: 'y',
      plugins: {
        title: {
          display: true,
          text: '🏷️ Top 12 Tags by Frequency',
          font: { size: 16, weight: 'bold' }
        },
        legend: { display: true }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { 
            stepSize: 1,
            font: { size: 11 }
          }
        },
        y: {
          ticks: {
            font: { size: 11 }
          }
        }
      }
    }
  };
  
  window.renderChart(chartData, this.container);
}
```

---

## 😤 MOOD INFLUENCERS

### 🏆 Top 12 Mood Influencers
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"');
const influencers = {};

pages.forEach(page => {
  if (page['mood-influencers'] && Array.isArray(page['mood-influencers'])) {
    page['mood-influencers'].forEach(inf => {
      influencers[inf] = (influencers[inf] || 0) + 1;
    });
  }
});

const sorted = Object.entries(influencers)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 12);

let chart = {
  type: 'bar',
  data: {
    labels: sorted.map(s => s[0]),
    datasets: [
      {
        label: 'Frequency',
        data: sorted.map(s => s[1]),
        borderColor: '#f59e0b',
        backgroundColor: '#f59e0b33',
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }
    ]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: { ticks: { font: { size: 11 } } },
      y: { ticks: { font: { size: 11 } } }
    }
  }
};

window.renderChart(chart, this.container);
```

---

## 📈 ANALYSIS INSIGHTS

### High Stress Days (5+ moods)
```dataview
TABLE
  file.name as "📝 Date",
  length(mood) as "😠 Moods",
  mood as "Moods"
FROM "PERSONAL/Daily Notes"
WHERE length(mood) >= 5
SORT file.name DESC
LIMIT 15
```

### 😰 Anxious/Worried Days
```dataview
TABLE
  file.name as "📝 Date",
  mood as "💭 Moods"
FROM "PERSONAL/Daily Notes"
WHERE any(mood, (m) => contains(lower(m), "anxious") or contains(lower(m), "worried"))
SORT file.name DESC
LIMIT 10
```

### 😢 Sad/Hopeless Days
```dataview
TABLE
  file.name as "📝 Date",
  mood as "💭 Moods"
FROM "PERSONAL/Daily Notes"
WHERE any(mood, (m) => contains(lower(m), "sad") or contains(lower(m), "hopeless"))
SORT file.name DESC
LIMIT 10
```

---

## 📊 COMPREHENSIVE DATA TABLES

### All Moods (Complete List)
```dataview
TABLE WITHOUT ID
  mood_item as "Mood",
  length(rows) as "Count",
  round(length(rows) / 40 * 100, 1) as "%"
FROM "PERSONAL/Daily Notes"
WHERE mood
FLATTEN mood as mood_item
GROUP BY mood_item
SORT length(rows) DESC
```

### All Topics (Complete List)
```dataview
TABLE WITHOUT ID
  topic_item as "Topic",
  length(rows) as "Count",
  round(length(rows) / 40 * 100, 1) as "%"
FROM "PERSONAL/Daily Notes"
WHERE topics
FLATTEN topics as topic_item
GROUP BY topic_item
SORT length(rows) DESC
```

### All Tags (Complete List)
```dataview
TABLE WITHOUT ID
  tag_item as "Tag",
  length(rows) as "Count",
  round(length(rows) / 40 * 100, 1) as "%"
FROM "PERSONAL/Daily Notes"
FLATTEN file.tags as tag_item
GROUP BY tag_item
SORT length(rows) DESC
```

### All Influencers (Complete List)
```dataview
TABLE WITHOUT ID
  influencer as "Influencer",
  length(rows) as "Count",
  round(length(rows) / 40 * 100, 1) as "%"
FROM "PERSONAL/Daily Notes"
WHERE mood-influencers
FLATTEN mood-influencers as influencer
GROUP BY influencer
SORT length(rows) DESC
```

---

## 📝 TOPICS & TAGS BY DATE

### Topics Distribution by Date
```dataview
TABLE
  file.name as "📝 Date",
  length(topics) as "🎯 Topics",
  topics as "�� Topics List"
FROM "PERSONAL/Daily Notes"
WHERE topics
SORT file.name DESC
LIMIT 20
```

### Tags Distribution by Date
```dataview
TABLE
  file.name as "📝 Date",
  length(file.tags) as "🏷️ Tags",
  file.tags as "🔖 Tags List"
FROM "PERSONAL/Daily Notes"
SORT file.name DESC
LIMIT 20
```

---

## 📅 RECENT DAILY NOTES

### Recent Entries (Last 20)
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"').filter(p => p.file && p.file.name);

dv.paragraph(`
### 📋 Most Recent Notes

| 📝 Date | 😊 Moods | 🎯 Topics | 🏷️ Tags |
|:---|:---:|:---:|:---:|
${pages.slice(0, 20).map(p => {
  const mood = p.mood && Array.isArray(p.mood) ? p.mood.length : 0;
  const topics = p.topics && Array.isArray(p.topics) ? p.topics.length : 0;
  const tags = p.file.tags && Array.isArray(p.file.tags) ? p.file.tags.length : 0;
  
  return `| [[${p.file.name}|${p.file.name}]] | ${mood} | ${topics} | ${tags} |`;
}).join('\n')}
`);
```

### All Daily Notes
```dataview
TABLE
  file.name as "📝 Date",
  length(mood) as "😊 Moods",
  mood as "Moods"
FROM "PERSONAL/Daily Notes"
SORT file.name DESC
```

---

## ⚙️ DASHBOARD INFORMATION

**Layout & Design:**
- 📊 Daily notes snapshot with metrics
- 💭 Mood analysis (top 15 + distribution)
- 📚 Topics breakdown (top 12)
- 🏷️ Tags analysis (top 12, including inline)
- 😤 Mood influencers (top 12)
- 📈 Analysis insights (stress days, worries, sadness)
- 📋 Complete data tables (all moods, topics, tags, influencers)
- 📅 Recent entries

**Features:**
✅ Real-time calculations
✅ Percentage calculations
✅ Horizontal bar charts for easy reading
✅ Doughnut chart for mood distribution
✅ Both frontmatter + inline tags tracked
✅ Status indicators (😊 💭 🎯 🏷️)
✅ Complete data with percentages
✅ Recent entries highlighted
✅ Analysis of negative emotions

**Data Completeness:**
- All notes from PERSONAL/Daily Notes folder
- Dynamic calculations (no hard-coded values)
- All moods tracked
- All topics tracked
- All tags tracked (frontmatter + inline)
- All mood influencers tracked
- Complete note history with dates

**Last Updated:** 2025-12-07 17:44 UTC
