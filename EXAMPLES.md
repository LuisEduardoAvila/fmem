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
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: You Send Message                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━                                      │
│  You → OpenClaw → "Remember my favorite movies are..."          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Trigger Detection                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━                                         │
│  I run: should_search("Remember my favorite movies...")         │
│  Result: True ✓ ("remember" + "movies" matches AGENTS.md)         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Parse & Store                                          │
│  ━━━━━━━━━━━━━━━━━━━━                                           │
│  I extract: ["Gladiator", "Idiocracy", "Tour de Pharmacy"]       │
│                                                                 │
│  I write to: memory/2026-02-15.md                               │
│  ## Movie Preferences - 2026-02-15                              │
│  **Favorite Movies:**                                           │
│  - Gladiator                                                    │
│  - Idiocracy                                                    │
│  - Tour de Pharmacy                                             │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Index with fmem                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━                                         │
│  fmem.add_document("memory/2026-02-15.md", chunk_by_sections)   │
│                                                                 │
│  Indexed: → FAISS vector index                                    │
│           → SQLite metadata database                              │
│  (Now searchable for future queries)                              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: I Confirm                                              │
│  ━━━━━━━━━━━━━━━━━                                              │
└─────────────────────────────────────────────────────────────────┘
```

**I respond:**
> "Got it! I've saved your favorite movies: Gladiator, Idiocracy, and Tour de Pharmacy. I'll remember these for future recommendations."

---

### Step 2: Get Recommendations (How It Actually Works)

**Later you say:**
> "Suggest a movie for my watchlist"

**Here's the actual flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: You Send Message                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━                                      │
│  You → OpenClaw → "Suggest a movie for my watchlist"            │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: I Receive Your Message                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                 │
│  What I see: "Suggest a movie for my watchlist"                 │
│  (Just your text. Nothing else yet.)                            │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: I Check AGENTS.md (Every Session)                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                              │
│  AGENTS.md tells me: "Check if memory is relevant"                │
│                                                                 │
│  I run: should_search("Suggest a movie...")                     │
│  Result: True ✓ (because "movie" + "suggest" match triggers)    │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: I CALL fmem MYSELF                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━                                     │
│  I execute: auto_recall("suggest movie watchlist", top_k=3)     │
│                                                                 │
│  fmem searches FAISS index...                                   │
│  Returns: [2026-02-15.md#Movie Preferences]                     │
│           ("Gladiator, Idiocracy, Tour de Pharmacy")            │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: I NOW Have Context                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━                                      │
│  My internal state:                                             │
│  • User asked for movie suggestions                             │
│  • I found: Favorite movies = Gladiator, Idiocracy...           │
│  • I "remember" your preferences                                  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: I Respond                                              │
│  ━━━━━━━━━━━━━━━━━                                              │
│  Based on the fmem results I just retrieved:                    │
└─────────────────────────────────────────────────────────────────┘
```

**I respond:**
> Based on your love of **epic dramas** (Gladiator) and **intelligent comedies** (Idiocracy, Tour de Pharmacy):
> 
> 1. **The Big Short** - Smart finance comedy like Idiocracy
> 2. **Dune** - Epic sci-fi drama
> 3. **Don't Look Up** - Satirical comedy with serious themes

**Key Point:** I **actively decide** to search fmem based on trigger words. The memory doesn't appear automatically—I retrieve it when your message matches the patterns in AGENTS.md.

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

## 🏗️ How fmem Works (Architecture)

### Current Implementation: Option 1 (AGENTS.md)

**This is what you just saw above.** The flow is:

```
You → Message → AGENTS.md Check → should_search()? 
                                      ↓
                             True: I call auto_recall()
                                      ↓
                              Results added to my context
                                      ↓
                              I respond with memory
```

**Key Characteristic:** **I decide when to search.** Your message triggers the check, but I actively call fmem only when patterns match.

### Future: Option B (Automatic Hook) - Planned

**Different approach:** OpenClaw would search **before** I see your message:

```
You → Message → OpenClaw Auto-Searches fmem → Injects results
                                              ↓
                              I receive message + context
                                              ↓
                              I "just know" without deciding
```

**Key Difference:** **Automatic injection.** Every message gets searched, results injected if relevant. I don't decide—it's automatic.

### Comparison

| Aspect | Option 1 (Current) | Option B (Future) |
|--------|-------------------|-------------------|
| **Who searches?** | I search after seeing message | OpenClaw searches before I see it |
| **When does memory appear?** | After I decide to call fmem | Before I process message |
| **Do I "just know"?** | ❌ No, I actively retrieve | ✅ Yes, it's in my context |
| **Misses context?** | Possible if no trigger | Catches everything |
| **Speed** | Fast | Slightly slower |
| **Implementation** | ✅ Live now | 📋 Planned (Phase 2B) |

**Bottom Line:** Option 1 requires me to **actively retrieve** when triggers match. Option B would make memory **automatically present** in every conversation.

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
