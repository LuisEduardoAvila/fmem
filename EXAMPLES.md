# fmem Examples

Real-world workflows demonstrating fmem's automatic memory recall.

---

## 🎬 Workflow 1: Movie Recommendations

**Scenario:** You tell me your favorite movies, then later ask for recommendations.

### Step 1: Remember Your Favorites

**You say:**
> "Remember my favorite movies are Gladiator, Idiocracy, and Tour de Pharmacy"

**What happens:**

```
┌─────────────────────────────────────────────────────────────┐
│  1. DETECT     → "remember" + "movies" (AGENTS.md trigger)  │
│  2. PARSE      → Extract: ["Gladiator", "Idiocracy",         │
│                          "Tour de Pharmacy"]                  │
│  3. WRITE      → memory/2026-02-15.md                       │
│  4. INDEX      → fmem.add_document() → FAISS + SQLite        │
│  5. CONFIRM    → "Got it! I'll remember that."              │
└─────────────────────────────────────────────────────────────┘
```

**Stored in memory:**
```markdown
## Movie Preferences - 2026-02-15

**Favorite Movies:**
- Gladiator
- Idiocracy
- Tour de Pharmacy

**Genres:** Epic historical drama, intelligent satirical comedy
```

---

### Step 2: Get Recommendations

**Later you say:**
> "Suggest a movie for my watchlist"

**What happens:**

```
┌─────────────────────────────────────────────────────────────┐
│  1. DETECT     → "movie" + "suggest" → should_search() True  │
│  2. RECALL     → auto_recall("suggest movie watchlist")        │
│  3. FIND       → [2026-02-15.md#Movie Preferences]            │
│  4. ANALYZE    → "likes: epic dramas + satirical comedy"      │
│  5. SUGGEST    → Based on your taste profile...             │
└─────────────────────────────────────────────────────────────┘
```

**I respond:**
> Based on your love of **epic dramas** (Gladiator) and **intelligent comedies** (Idiocracy, Tour de Pharmacy):
> 
> 1. **The Big Short** - Smart finance comedy like Idiocracy
> 2. **Dune** - Epic sci-fi drama
> 3. **Don't Look Up** - Satirical comedy with serious themes

---

## 🏋️ Workflow 2: Fitness Tracking

**Scenario:** Remember your workout schedule, later check availability.

### Step 1: Set Schedule

**You say:**
> "Remember I want to work out Mondays and Thursdays at 6pm"

**Stored:** `memory/2026-02-15.md` → ## Fitness Routine

### Step 2: Check Schedule + Suggest

**Later you say:**
> "What's my schedule this week?"

**I recall:**
- Fitness goal: Workouts Mon/Thu at 6pm
- Calendar check: Monday meeting → free Thursday

**I respond:**
> This week: Monday is busy with meetings, but **Thursday 6pm** is free for your workout!

---

## 💻 Workflow 3: Project Context

**Scenario:** Track what you're working on and get relevant suggestions.

### Step 1: Remember Project

**You say:**
> "Remember I'm building an MCP server for fmem integration"

**Stored:** `memory/2026-02-15.md` → ## Active Projects

### Step 2: Get Context-Aware Help

**Later you say:**
> "What should I work on?"

**I recall:**
- Active project: MCP server for fmem
- ROADMAP.md → Phase 3
- Current task: TypeScript server setup

**I respond:**
> You're in **Phase 3** of the fmem MCP wrapper. Next step: TypeScript server scaffolding. Want help setting up the MCP protocol handlers?

---

## 📊 Why This Works

| Feature | Benefit |
|---------|---------|
| **Automatic Detection** | No commands to memorize - just talk naturally |
| **Context Preservation** | I remember your preferences, not just facts |
| **Pattern Recognition** | "suggest" + "movie" → recall preferences |
| **Combined Retrieval** | fmem + calendar + roadmap = complete answer |

---

## 🎯 Try Yourself

**Copy-paste these:**

1. **Set preference:**
   > Remember my coffee order is flat white with oat milk

2. **Test recall:**
   > What do I usually drink?

3. **Set goals:**
   > Remember my Q1 goal is learning Rust

4. **Query context:**
   > What should I focus on this quarter?

---

## 📝 Key Triggers

**Automatic recall activates on:**

| Type | Examples |
|------|----------|
| Explicit | "remember", "recall", "what about" |
| Context | "fitness", "movies", "projects" |
| Time | "last week", "previous", "recently" |
| Personal | "my goals", "my preferences", "my schedule" |

See [AGENTS.md](../AGENTS.md) for complete trigger patterns.

---

## 🔗 Related

- [AGENTS.md](../AGENTS.md) - Trigger patterns and integration
- [README.md](../README.md) - Installation and usage
- [README.md#🤖 Enable Agent Integration](../README.md#-enable-agent-integration) - First-time setup
