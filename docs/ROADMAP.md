# DisSysLab Development Roadmap

## Current Status: Version 1.0 → 1++

We have a working version 1.0 with core functionality. Before moving to version 2.0 (which adds cycles, snapshots, and termination detection), we need to polish 1.0 into 1++ with improved documentation and examples.

---

## Phase 1: Core Infrastructure Polish (Version 1++)

### Documentation
- [x] Create `ROADMAP.md` (this file)
- [x] Create `DOCUMENTATION_STRATEGY.md` 
- [x] Create `docs/HOW_IT_WORKS.md` - student-friendly overview
- [ ] Create `docs/API_REFERENCE.md` - complete API documentation
- [ ] Create `docs/ARCHITECTURE.md` - system internals
- [ ] Create `CONTRIBUTING.md` - contribution guidelines
- [ ] Create `TROUBLESHOOTING.md` - common errors and solutions

### Code Quality
- [ ] Add comprehensive docstrings to all modules
- [ ] Add type hints throughout codebase
- [ ] Fix the transform.py escape sequence warning
- [ ] Review and test all decorator patterns
- [ ] Ensure consistent error messages

### Examples and Modules
- [x] Reorganize from `ch##_*` to topic-based names
- [x] Create `modules/basic/` with social media example
- [ ] Create `modules/filtering/` - demonstrate None-dropping
- [ ] Create `modules/numeric/` - NumPy/pandas examples
- [ ] Create `modules/ml/` - scikit-learn pipeline
- [ ] Create `modules/text_nlp/` - text processing
- [ ] Create `modules/data_pipeline/` - file I/O and ETL
- [ ] Add README.md to each module explaining concepts

### Testing
- [ ] Write unit tests for decorators
- [ ] Write integration tests for network compilation
- [ ] Test all example modules
- [ ] Add CI/CD pipeline (GitHub Actions)

---

## Phase 2: Version 2.0 Features

### Major Additions
- [ ] **Cycles in Networks** - support feedback loops
- [ ] **Global Snapshots** - Chandy-Lamport algorithm
- [ ] **Termination Detection** - distributed termination protocol
- [ ] **Concurrent Modification** - safe network updates while running

### Additional Features
- [ ] Network visualization (generate topology diagrams)
- [ ] Performance monitoring and metrics
- [ ] Debug mode with message tracing
- [ ] Replay capability for debugging

---

## Phase 3: Advanced Features (Future)

- [ ] Fault tolerance and recovery
- [ ] Network partitioning simulation
- [ ] Time-based message scheduling
- [ ] Priority queues and message ordering
- [ ] State persistence and recovery

---

## Timeline

**Version 1++ (Current Focus):** 4-6 weeks
- Week 1-2: Documentation and module organization
- Week 3-4: Testing and code quality
- Week 5-6: Final polish and release prep

**Version 2.0:** 8-10 weeks after 1++ release
- Cycles and snapshots are complex features requiring careful design

---

## Success Criteria for Version 1++

Before moving to 2.0, we need:
1. ✅ All core documentation complete
2. ✅ 6-8 well-documented example modules
3. ✅ Zero known bugs in core infrastructure
4. ✅ All examples tested and working
5. ✅ Comprehensive troubleshooting guide
6. ✅ Student feedback incorporated (after first course offering)

---

*Last updated: January 2026*