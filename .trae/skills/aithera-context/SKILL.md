---
name: "aithera-context"
description: "Automatically reviews Aithera project context files (Systems Schema, Development Documentation, and system logs) before performing any task. Essential for understanding project state and recent issues."
---

# Aithera Context Reviewer

This skill automatically reviews the three essential context files for the Aithera project to ensure any work is performed with full awareness of the project state, existing functionalities, and recent issues.

## When to Invoke

**MANDATORY: Invoke this skill FIRST before working on ANY task in the Aithera project, including:**
- Bug fixes
- Feature development
- Code refactoring
- Documentation updates
- Testing
- Debugging
- Any other development work

**Do NOT skip this review** even for "small" changes - understanding the context prevents conflicts and ensures consistency.

## Files to Review

### 1. Systems Schema (`Systems Schema.md`)
**Purpose**: Complete inventory of all functionalities, features, and system capabilities.

**What to check:**
- All implemented features
- Current project state
- API endpoints available
- Database models
- UI components
- AI providers and agents

**Review depth**: Full review - understand what's already built before adding new features.

### 2. Development Documentation (`Documentación de Desarrollo.md`)
**Purpose**: Development history, technical decisions, and project evolution.

**What to check:**
- Development phases and completion status
- Technical decisions and rationale
- Known issues and problems
- Configuration details
- How to continue development
- Commands and setup instructions

**Review depth**: Focus on sections relevant to your current task.

### 3. System Logs (`backend/logs/`)
**Purpose**: Recent errors and system events for debugging context.

**What to check:**
- Recent errors (errors.log)
- System events (system.log)
- Timestamps of issues
- Error patterns
- Module-specific issues

**Review depth**: Check logs from the last session or most recent errors.

## Review Process

### Step 1: Read Systems Schema
```
Read: Systems Schema.md
```
- Understand all existing functionalities
- Note current implementation state
- Identify if feature already exists

### Step 2: Read Development Documentation
```
Read: Documentación de Desarrollo.md
```
- Check current development phase
- Review known issues
- Understand technical context
- Note important configuration

### Step 3: Check Recent Logs
```
Read: backend/logs/errors.log (last 50 lines)
Read: backend/logs/system.log (last 30 lines)
```
- Identify recent errors
- Note error patterns
- Check which modules have issues

### Step 4: Synthesize Context
After reviewing all three files, create a mental summary:

1. **What exists**: List key existing features relevant to the task
2. **Current issues**: Note any known problems or recent errors
3. **Technical context**: Remember configuration and setup details
4. **Progress status**: Know which development phases are complete

## Output Format

After reviewing, acknowledge what you found:

```
📋 Aithera Context Review Complete:

✅ Systems Schema: Reviewed
   - Key features: [list 2-3 most relevant]
   - Implementation status: [e.g., "Backend complete, Desktop in progress"]

📝 Development Documentation: Reviewed  
   - Development phase: [current phase]
   - Known issues: [list any relevant]
   - Technical decisions: [note important ones]

⚠️ Recent Logs: [Reviewed/None found]
   - Last error: [timestamp and brief description if exists]
   - Affected modules: [list modules with issues]

🎯 Ready to work on: [brief description of the task]
```

## Important Notes

### Before Making Changes

1. **Check Systems Schema first** - Don't duplicate existing functionality
2. **Review known issues** - Avoid repeating known problems
3. **Check logs** - Recent errors may indicate related issues
4. **Understand context** - Know why things are built the way they are

### After Making Changes

1. **Update documentation** if you add features or change behavior
2. **Add logs** appropriately for new functionality
3. **Note issues** if you discover new problems
4. **Update Systems Schema** if you add new features

### For Debugging Tasks

1. Always check `backend/logs/errors.log` first
2. Look for patterns in recent errors
3. Check which module is failing
4. Review relevant documentation sections

## File Locations

All files are in the project root:
- Project root: `c:\Users\Alejandro\Desktop\Aithera\`
- Systems Schema: `Systems Schema.md`
- Development Docs: `Documentación de Desarrollo.md`
- Logs directory: `backend/logs/`
  - System logs: `backend/logs/system.log`
  - Error logs: `backend/logs/errors.log`

## Quick Commands

To quickly review context:

```bash
# Read Systems Schema (first 100 lines)
head -n 100 "Systems Schema.md"

# Read recent errors
tail -n 20 "backend/logs/errors.log"

# Read recent system events
tail -n 30 "backend/logs/system.log"
```

## Example Workflow

**Task**: Add a new API endpoint for user authentication

**Context Review Steps:**
1. Read Systems Schema → Find existing API endpoints structure
2. Read Development Docs → Check why there's no auth yet (known issue)
3. Check logs → No recent auth-related errors
4. Synthesis → Backend API complete, auth is "pending" in known issues

**Result**: Proceed with auth implementation knowing:
- Follow existing API pattern
- Auth is planned but not yet implemented
- No conflicting recent errors
- Update documentation to mark auth as "in progress"

---

**Remember**: Context review prevents 80% of common development mistakes. Always review before acting!
