# Coverage Analysis: Remaining 7% Uncovered Code

**Overall Coverage**: 93% (330 tests, 91 uncovered lines out of 1,379 total)

## Summary by Category

### Worth Testing (High Value)
**~55 lines (4% of codebase) - Would improve coverage to ~97%**

1. **SQL Upload in `depivot_multi_file`** (55 lines)
   - Lines 941-995 in core.py
   - **Impact**: HIGH - This is a major feature path
   - **Effort**: MEDIUM - Similar to existing SQL upload tests
   - **Recommendation**: **ADD TESTS** - This is the same SQL upload logic as in `depivot_file`, but in the multi-file wildcard processor

### Acceptable to Leave Uncovered (Low Value)
**~36 lines (3% of codebase)**

#### 1. Entry Point Boilerplate (6 lines)
- `__main__.py` lines 3-6: Module entry point
- `cli.py` line 537: Script entry point
- **Why Skip**: Trivial boilerplate, testing provides no value
- **Coverage Impact**: 0.4%

#### 2. Verbose Output Messages (10 lines)
- `core.py` lines 732, 746: Verbose output in combine sheets mode
- `sql_upload.py` line 196: Verbose fiscal year extraction message
- `data_quality.py` lines 301, 310: Verbose validation details
- **Why Skip**: Optional console output, no business logic
- **Coverage Impact**: 0.7%

#### 3. Exception Cleanup Code (8 lines)
- `sql_upload.py` lines 331-332: Rollback on error
- `sql_upload.py` lines 341-342: Connection cleanup
- **Why Skip**: Defensive cleanup code that's hard to trigger in tests
- **Coverage Impact**: 0.6%

#### 4. Error Handling Edge Cases (12 lines)
- `cli.py` lines 317-318: Config save error handling
- `cli.py` lines 461-467: Batch config save error handling
- `core.py` lines 755-756: File write error handling
- `core.py` lines 893-895: Sheet processing error handling
- `core.py` lines 1012-1013: Multi-file write error handling
- `sql_upload.py` lines 200-203: Fiscal year extraction error
- `sql_upload.py` lines 285-286: Truncate table error
- `data_quality.py` lines 178-180: Rule loading error
- **Why Skip**: Hard to trigger without mocking OS/file system failures
- **Coverage Impact**: 0.9%

## Detailed Analysis by Module

### src/depivot/__main__.py (0% - 3 lines)
**Status**: ✅ Acceptable

```python
3: from depivot.cli import main
5: if __name__ == "__main__":
6:     main()
```

**Analysis**: Module entry point boilerplate. Only executed when running `python -m depivot`. No business logic.

---

### src/depivot/cli.py (94% - 12 lines missing)
**Status**: ✅ Acceptable (except line 494)

#### Lines 317-318: Config Save Error
```python
317: except Exception as e:
318:     raise DepivotError(f"Error saving config file {save_config}: {e}")
```
**Category**: Error handling
**Reason**: Requires OS-level file write failure

#### Lines 461-467: Batch Config Save Error
```python
461-467: try/except block for config save
```
**Category**: Error handling
**Reason**: Duplicate of above in different code path

#### Line 494: Wildcard Without Output Path
```python
494: raise DepivotError("For wildcard processing, OUTPUT_PATH must be specified")
```
**Category**: Error handling
**Reason**: Could test, but low value - CLI validation error

#### Line 516: Auto-generate Output Filename
```python
516: output_path_obj = generate_output_filename(input_path_obj, suffix)
```
**Category**: Default behavior
**Reason**: Should be tested, but low priority

#### Line 537: Script Entry Point
```python
537: main()
```
**Category**: Boilerplate
**Reason**: Entry point, no logic

---

### src/depivot/core.py (91% - 36 lines missing)
**Status**: ⚠️ **IMPORTANT GAP** in lines 941-995

#### Lines 732, 746: Verbose Output
```python
732: console.print(f"[green]Combined {len(depivoted_sheets)} sheet(s)...")
746: sheet_count = 1  # Just the combined sheet
```
**Category**: Verbose output
**Reason**: Non-critical console messages

#### Lines 755-756: File Write Error
```python
755: except Exception as e:
756:     raise FileProcessingError(f"Error writing output file {output_file}: {e}")
```
**Category**: Error handling
**Reason**: Requires file system failure

#### Line 869: Forecast Split in Multi-file
```python
869: df_long[data_type_col] = df_long[var_name].apply(...)
```
**Category**: Business logic in depivot_multi_file
**Reason**: Not tested because depivot_multi_file has limited test coverage

#### Line 881: ReleaseDate in Multi-file
```python
881: df_long["ReleaseDate"] = release_date
```
**Category**: Business logic in depivot_multi_file
**Reason**: Same as above

#### Lines 893-895: Sheet Processing Error
```python
893: except Exception as e:
894:     console.print(f"[red]ERROR processing...")
895:     raise FileProcessingError(...)
```
**Category**: Error handling
**Reason**: Requires sheet processing to fail

#### Lines 926-929: Validation Mismatch Warning
```python
926: console.print("[yellow]WARNING: Validation found mismatches![/yellow]")
927-929: Mismatch summary output
```
**Category**: Warning output
**Reason**: Only triggered when validation finds mismatches

#### ⚠️ Lines 941-995: SQL Upload in depivot_multi_file (55 LINES)
```python
941-995: Complete SQL upload logic in depivot_multi_file
```
**Category**: **MAJOR FEATURE PATH**
**Reason**: SQL upload is tested in `depivot_file` and `depivot_batch`, but NOT in `depivot_multi_file`
**Impact**: This is 4% of the entire codebase
**Recommendation**: **ADD INTEGRATION TEST** for wildcard multi-file with SQL upload

#### Lines 1012-1013: File Write Error
```python
1012: except Exception as e:
1013:     raise FileProcessingError(f"Error writing output file...")
```
**Category**: Error handling
**Reason**: Duplicate of 755-756 in different function

---

### src/depivot/sql_upload.py (92% - 11 lines missing)
**Status**: ✅ Acceptable

#### Line 196: Verbose FiscalYear Message
```python
196: console.print("[cyan]Extracting FiscalYear from ReleaseDate...[/cyan]")
```
**Category**: Verbose output
**Reason**: Non-critical console message

#### Lines 200-203: FiscalYear Extraction Error
```python
200: except ValueError as e:
201-203: Warning output and set to None
```
**Category**: Error handling
**Reason**: Requires invalid date format

#### Lines 285-286: Truncate Table Error
```python
285: except pyodbc.Error as e:
286:     console.print(f"[yellow]Warning: Could not truncate table...")
```
**Category**: Error handling
**Reason**: Requires database permission error

#### Lines 331-332: Rollback Cleanup
```python
331: except:
332:     pass
```
**Category**: Defensive cleanup
**Reason**: Exception cleanup, hard to trigger

#### Lines 341-342: Connection Cleanup
```python
341: except:
342:     pass
```
**Category**: Defensive cleanup
**Reason**: Exception cleanup, hard to trigger

---

### src/depivot/data_quality.py (95% - 6 lines missing)
**Status**: ✅ Acceptable

#### Line 83: Abstract Method Pass
```python
83: pass
```
**Category**: Abstract method placeholder
**Reason**: Never executed, just abstract base class

#### Lines 178-180: Rule Loading Error
```python
178: except Exception as e:
179:     console.print(f"[yellow]Warning: Failed to load rule...")
180:     continue
```
**Category**: Error handling
**Reason**: Requires invalid rule configuration

#### Lines 301, 310: Verbose Validation Details
```python
301: console.print(f"    Details: {result.details}")
310: console.print(f"    Details: {result.details}")
```
**Category**: Verbose output
**Reason**: Non-critical console messages

---

### src/depivot/quality_rules.py (93% - 15 lines missing)
**Status**: ✅ Acceptable

All missing lines are defensive checks:
- Lines 45, 243, 441, 517, 531, 613, 627, 640, 718: `if col not in df.columns: continue`
- Lines 251-252, 732-733, 738-739: Exception handling for type conversion errors

**Category**: Defensive programming
**Reason**: Edge cases for missing columns or invalid data types

---

### src/depivot/template_validators.py (96% - 8 lines missing)
**Status**: ✅ Acceptable

All missing lines are error handling or edge cases:
- Line 123: Abstract method pass statement
- Lines 328-330: Missing column handling
- Line 334: Column ordering check edge case
- Line 374: Merged cells detection edge case
- Line 383: Numeric format validation edge case
- Line 437: DataFrame column check edge case

**Category**: Error handling and edge cases
**Reason**: Hard to trigger without specific Excel file configurations

---

## Recommendations

### Priority 1: High-Value Test (Recommended)
**Add SQL upload test for `depivot_multi_file`** - Lines 941-995 in core.py

**Impact**:
- Coverage: 93% → ~97% (+4%)
- Tests major feature path that's currently completely uncovered
- Similar effort to existing SQL upload tests

**Implementation**:
```python
# In test_integration.py
@patch('depivot.sql_upload.upload_to_sql_server')
@patch('depivot.sql_upload.transform_dataframe_for_sql')
@patch('depivot.sql_upload.fetch_l2_proj_mapping')
def test_depivot_multi_file_sql_upload(mock_fetch, mock_transform, mock_upload, temp_dir):
    """Test depivot_multi_file with SQL upload (wildcard processing)."""
    # Create multiple test files matching wildcard pattern
    # Test with --sql-only flag
    # Verify SQL upload was called
```

### Priority 2: Low-Value Tests (Optional)
Could add tests for validation mismatches, verbose output paths, etc., but these provide diminishing returns.

### Not Recommended
- Entry point boilerplate (__main__.py, cli.py:537)
- Exception cleanup code (sql_upload.py:331-332, 341-342)
- Abstract method pass statements

---

## Conclusion

**Current State**: 93% coverage is excellent for a production application

**Recommendation**:
1. **Add SQL upload test for `depivot_multi_file`** → ~97% coverage
2. **Stop at 97%** - The remaining 3% is low-value code (error handlers, verbose output, boilerplate)

**Rationale**:
- 97% is industry-leading coverage
- The uncovered 3% is defensive programming that's hard to test
- Effort to reach 99-100% coverage has very low ROI
- Tests should focus on business logic, not OS-level failure scenarios

**Alternative**: Accept 93% coverage as-is
- The main SQL upload paths ARE tested (depivot_file, depivot_batch)
- depivot_multi_file is a less common code path (wildcard processing)
- 93% is already excellent coverage

---

**Date**: January 6, 2026
**Analysis Version**: 1.0
**Coverage Tool**: pytest-cov
