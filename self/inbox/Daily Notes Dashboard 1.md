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
- inbox
created: 2025-12-05T19:35
updated: 2025-12-07T22:52
---

# 📓 Daily Notes Dashboard

---

> [!info]- 📊 SUMMARY SNAPSHOT & 🎯 MOOD ANALYSIS

## 📊 Summary Metrics
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
| 📊 Metric | Value |
|:---|---:|
| 📝 Total Notes | **${pages.length}** |
| 😊 Notes w/ Mood | **${pagesWithMood.length}** |
| 😢 Unique Moods | **${uniqueMoods.size}** |
| 🎯 Unique Topics | **${uniqueTopics.size}** |
| 🏷️ Unique Tags | **${uniqueTags.size}** |
| 💭 Avg Moods/Note | **${(totalMoods/pagesWithMood.length).toFixed(1)}** |
`);
```

---

## 🏆 Top 15 Moods
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

---

## 📅 Activity Heatmap

### 2025 Daily Notes Contribution

```dataviewjs
const trackerData = {
    year: 2025,
    entries: [],
    heatmapTitle: "📅 <b>2025 Daily Notes Activity</b>",
    heatmapSubtitle: "Journaling consistency throughout the year",
    separateMonths: true,
    showCurrentDayBorder: true,
    defaultEntryIntensity: 1
}

const allPages = dv.pages('"PERSONAL/Daily Notes"') || [];

for(let page of allPages){
    let dateStr = null;
    
    if(page.file.name === 'Daily Notes Dashboard.md') {
        continue;
    }
    
    if(page.created) {
        const createdDate = new Date(page.created);
        if(!isNaN(createdDate)) {
            dateStr = createdDate.toISOString().split('T')[0];
        }
    }
    
    if(!dateStr && page.file && page.file.name) {
        const fileName = page.file.name.replace('.md', '').trim();
        
        let match = fileName.match(/(\d{4})-(\d{2})-(\d{2})/);
        if(match) {
            dateStr = `${match[1]}-${match[2]}-${match[3]}`;
        }
        
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
                }
            }
        }
        
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

## 📚 Top 12 Topics
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

## 😤 Top 12 Mood Influencers
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

## 📈 Analysis Insights

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

## 📊 Comprehensive Data Tables

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

---

## 📝 Recent Entries

### Recent Daily Notes (Last 20)
```dataviewjs
const pages = dv.pages('"PERSONAL/Daily Notes"').filter(p => p.file && p.file.name);

dv.paragraph(`
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

---

## ⚙️ Dashboard Information

**Features:**
✅ Real-time mood tracking & analysis
✅ Activity heatmap for 2025
✅ Top 15 moods with frequency charts
✅ Topics & tags distribution
✅ Mood influencers tracking
✅ Mental health insights (stress, anxiety, sadness)
✅ Complete data tables with percentages
✅ Recent entries summary

**Last Updated:** 2025-12-07 22:52 UTC
