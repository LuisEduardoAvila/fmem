# fmem Examples

Real-world workflows demonstrating fmem's automatic memory recall.

---

## 🎬 Workflow 1: Movie Recommendations

**Scenario:** You mention movies, then ask for suggestions. fmem finds what I already know about your preferences.

### Step 1: Ask for Suggestions (Conversational)

**You say:**
> "Remember my favorite movies. And suggest movies to watch?"

**Here's what actually happens:**

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: You Send Message                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━                                      │
│  You → OpenClaw → "Remember my favorite movies. And suggest..." │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: I Receive Your Message                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                 │
│  What I see: "Remember my favorite movies. And suggest..."      │
│  (Just your text. No movies listed yet.)                        │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: I Check AGENTS.md                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━                                     │
│  I run: should_search("Remember my favorite movies...")         │
│  Result: True ✓ ("remember" + "movies" triggers search)           │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: I CALL fmem to Search                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                 │
│  I execute: auto_recall("favorite movies suggest watch", top_k=3) │
│                                                                 │
│  fmem searches your indexed memory...                            │
│  Returns: [2026-02-13.md#Movie Preferences]                       │
│           "Movie/TV Preferences: Gladiator, Idiocracy..."        │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: I NOW Have Context                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━                                      │
│  My internal state:                                             │
│  • User wants movie suggestions                                 │
│  • I found: Past preferences include Gladiator, Idiocracy      │
│  • I can now suggest similar movies                              │
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
> I recall from our earlier chat that your favorites include **Gladiator** and **Idiocracy**. Based on those, try:
> 
> 1. **The Big Short** - Smart satire like Idiocracy
> 2. **Dune** - Epic sci-fi drama
> 3. **Don't Look Up** - Satirical comedy with serious themes
> 
> Are there any other favorites I should add to your list?

**Key Point:** You didn't list your favorites in this message, but fmem found them from a previous conversation. That's the magic - **contextual memory across sessions**.

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

## 🔗 Related

- [README.md](./README.md) - Installation and usage, architecture, and triggers
- [README.md#current-implementation-agentsmd-integration](./README.md#current-implementation-agentsmd-integration) - First-time setup
