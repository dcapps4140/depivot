# Critical Issues Found in Depivot Project

## Date: January 7, 2026
## Status: **REQUIRES IMMEDIATE ATTENTION**

---

## Issue #1: SQL Table Name Not Clearly Documented ❌

**Problem:**
- The SQL table name is a user-provided parameter (`--sql-table`)
- Examples in README show `[dbo].[Budget_Actuals]` but this is just an example
- **No way to determine what table was actually used in recent test runs**
- Costs_Module team cannot determine which table to query

**Impact:** HIGH - Cannot integrate with Costs_Module without knowing the actual table name

**Fix Required:**
1. Create a default/recommended table name
2. Document it prominently in README
3. Add to example config files
4. Create a SQL table creation script with the exact schema

---

## Issue #2: Missing Report Period Tracking ❌ **CRITICAL**

**Problem:**
The SQL schema has a critical data model flaw:

**Current Schema:**
```
L2_Proj, Site, Category, FiscalYear, Period, Actuals, Status
```

**What "Period" means:**
- Period (1-12) = The month the costs are **FOR** (e.g., January = 1, February = 2)

**What's MISSING:**
- **Report Period** = Which period the data was **REPORTED IN**
- ReleaseDate is used to extract FiscalYear, then **DISCARDED** (not uploaded!)

**Example of the problem:**
```
Data FOR January costs REPORTED IN March release
- Period = 1 (January costs)
- ReleaseDate = "2025-03" (reported in March)
- FiscalYear = 2025 (derived from ReleaseDate)

BUT after upload:
- Period = 1 ✓
- FiscalYear = 2025 ✓
- ReportPeriod = ??? ❌ (MISSING!)
- ReleaseDate = ??? ❌ (NOT STORED!)
```

**Why this matters:**
- Budget data is static (reported once)
- Actual data changes over time (revised in later releases)
- You need to know: "Give me P1 Actuals as reported in the P3 release"
- Current schema: Can only query "Give me P1 Actuals" (no way to know WHICH version/release)

**Impact:** CRITICAL - Cannot track data revisions or historical releases

**Fix Required:**
Add ReleaseDate or ReportPeriod to SQL schema:

**Option A - Add ReleaseDate (DATE type):**
```sql
L2_Proj, Site, Category, FiscalYear, Period, Actuals, Status, ReleaseDate
```

**Option B - Add ReportPeriod (INT type):**
```sql
L2_Proj, Site, Category, FiscalYear, Period, Actuals, Status, ReportPeriod
```

**Option C - Add BOTH (recommended):**
```sql
L2_Proj, Site, Category, FiscalYear, Period, Actuals, Status, ReleaseDate, ReportPeriod
```

---

## Issue #3: Config Files Not Documented ❌

**Problem:**
- No example config YAML files in the repository
- README shows command-line examples, but no `--config` file examples
- Cannot determine what config was used in test runs
- `--save-config` feature exists but no saved configs in repo

**Impact:** MEDIUM - Users cannot easily replicate test runs or use config files

**Fix Required:**
1. Create example config files in `examples/` directory:
   - `examples/basic_config.yaml`
   - `examples/sql_upload_config.yaml`
   - `examples/validation_config.yaml`
2. Document config file format in README
3. Add "Configuration File Reference" section to DEVELOPMENT.md

---

## Issue #4: Obsolete Files in Project Root ❌

**Problem:**
Current root directory has several issues:
```
.coverage          - Test coverage data (should be .gitignored)
coverage.json      - Test coverage JSON (should be .gitignored)
htmlcov/           - HTML coverage report (should be .gitignored)
NDH6SA~M           - Temp file with weird name (should be deleted)
```

**Impact:** LOW - Makes project look messy, but doesn't affect functionality

**Fix Required:**
1. Update `.gitignore` to exclude:
   - `.coverage`
   - `coverage.json`
   - `htmlcov/`
   - `*.pyc`
   - `__pycache__/`
   - `.pytest_cache/`
2. Delete temp file `NDH6SA~M`
3. Clean up any other test artifacts

---

## Implementation Plan

### Priority 1: Fix Critical Data Model Issue (Issue #2)

**Step 1 - Update SQL Schema:**
```python
# In sql_upload.py, line 235:
# OLD:
final_columns = ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status"]

# NEW:
final_columns = ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status", "ReleaseDate"]
```

**Step 2 - Keep ReleaseDate column:**
```python
# In sql_upload.py, around line 194-207:
# Don't discard ReleaseDate after extracting FiscalYear
# Keep it in the DataFrame
```

**Step 3 - Update upload query:**
```python
# In sql_upload.py, line 289:
# OLD:
columns = ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status"]

# NEW:
columns = ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status", "ReleaseDate"]
```

**Step 4 - Create SQL table creation script:**
```sql
CREATE TABLE [dbo].[FY25_Budget_Actuals_DIBS] (
    L2_Proj VARCHAR(50),
    Site VARCHAR(100),
    Category VARCHAR(100),
    FiscalYear INT,
    Period INT,
    Actuals DECIMAL(18,2),
    Status VARCHAR(20),
    ReleaseDate VARCHAR(20),  -- Format: YYYY-MM or YYYY-MM-DD
    CONSTRAINT PK_BudgetActuals PRIMARY KEY (Site, Category, FiscalYear, Period, Status, ReleaseDate)
);

CREATE INDEX IX_Period ON [dbo].[FY25_Budget_Actuals_DIBS] (Period);
CREATE INDEX IX_Site ON [dbo].[FY25_Budget_Actuals_DIBS] (Site);
CREATE INDEX IX_Status ON [dbo].[FY25_Budget_Actuals_DIBS] (Status);
CREATE INDEX IX_ReleaseDate ON [dbo].[FY25_Budget_Actuals_DIBS] (ReleaseDate);
```

### Priority 2: Document Table Name (Issue #1)

**Step 1 - Choose official table name:**
Recommendation: `Intel_Project.dbo.FY25_Budget_Actuals_DIBS`

**Step 2 - Update README.md:**
- Add "SQL Server Table Schema" section
- Document the exact table name
- Show the CREATE TABLE script

**Step 3 - Create example config:**
```yaml
# examples/sql_upload_config.yaml
sql_connection_string: "Driver={ODBC Driver 18 for SQL Server};Server=naildc-srv1;Database=Intel_Project;UID=sa;PWD=***;Encrypt=no;TrustServerCertificate=yes"
sql_table: "[dbo].[FY25_Budget_Actuals_DIBS]"
sql_mode: "append"
sql_l2_lookup_table: "[dbo].[Intel_Site_Names]"
```

### Priority 3: Add Config File Examples (Issue #3)

Create config files in `examples/` directory.

### Priority 4: Clean Up Project (Issue #4)

Update `.gitignore` and remove obsolete files.

---

## Questions for User

Before implementing fixes, please confirm:

1. **Table Name:**
   - Should we use `Intel_Project.dbo.FY25_Budget_Actuals_DIBS` as the standard table name?
   - Or different name?

2. **ReleaseDate Format:**
   - Should ReleaseDate be stored as:
     - `DATE` type in SQL (e.g., `2025-03-15`)?
     - `VARCHAR(20)` type (e.g., `"2025-03"` or `"2025-03-15"`)?
     - `INT` ReportPeriod instead (e.g., `3` for March)?

3. **Data Model:**
   - Do you also need ReportPeriod as a separate column? (1-12 for which month it was reported)
   - Or is ReleaseDate sufficient?

4. **Backwards Compatibility:**
   - Existing data in SQL table will not have ReleaseDate
   - Should we:
     - Create NEW table with corrected schema?
     - Migrate existing data (how to handle missing ReleaseDate)?
     - Keep both tables?

---

## Impact Summary

| Issue | Severity | Impact | Effort to Fix |
|-------|----------|--------|---------------|
| #1 - Table name not documented | HIGH | Blocks integration | 1 hour |
| #2 - Missing report period tracking | **CRITICAL** | **Data model broken** | 3-4 hours |
| #3 - Config files missing | MEDIUM | Usability issue | 1 hour |
| #4 - Obsolete files | LOW | Project hygiene | 15 min |

**Total estimated effort: 5-6 hours**

---

**Next Steps:**
1. User confirms table name and ReleaseDate format
2. Implement fixes in order of priority
3. Update all tests to include ReleaseDate
4. Update documentation
5. Create migration plan for existing data
6. Bump version to 0.2.0 (breaking schema change)

