# Contributing to GitHub Roast & Rescue

Thank you for your interest in contributing to **GitHub Roast & Rescue**!

## Development Setup

1. **Prerequisites**:
   - Node.js 20+ (Node.js 22 LTS recommended)
   - npm 10+

2. **Clone & Install**:

   ```bash
   git clone https://github.com/dheeraj5765483/roast-and-rescue.git
   cd roast-and-rescue
   npm install
   ```

3. **Local Development Server**:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` to view the application dashboard.

## Quality Gates & Verification

Before submitting a Pull Request, ensure that all quality gates pass:

```bash
# Run code formatting check
npm run format:check

# Run static analysis and strict type checking (ESLint + TypeScript)
npm run lint

# Run all 31 automated tests (Unit, A11y WCAG 2.1 AA, Analyzer, API)
npm test

# Full validation gate
npm run validate
```

## Pull Request Guidelines

1. Create a feature branch from `main`: `git checkout -b feature/my-enhancement`.
2. Ensure 100% test pass rate across all suites.
3. Adhere to the established Neo-Brutalist design language.
4. Open a PR with clear problem statement, changes introduced, and verification evidence.
