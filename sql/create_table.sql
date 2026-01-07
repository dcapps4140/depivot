-- ============================================================================
-- SQL Server Table Creation Script for Depivot Upload
-- ============================================================================
-- Table: Intel_Project.dbo.FY25_Budget_Actuals_DIBS
-- Purpose: Store budget and actual financial data from depivoted Excel files
-- Created: January 7, 2026
-- ============================================================================

USE Intel_Project;
GO

-- Drop table if it exists (WARNING: This will delete all data!)
IF OBJECT_ID('dbo.FY25_Budget_Actuals_DIBS', 'U') IS NOT NULL
BEGIN
    PRINT 'Dropping existing table dbo.FY25_Budget_Actuals_DIBS...'
    DROP TABLE dbo.FY25_Budget_Actuals_DIBS;
END
GO

-- Create the table
CREATE TABLE dbo.FY25_Budget_Actuals_DIBS
(
    -- Core identifiers
    L2_Proj         VARCHAR(50)     NULL,           -- L2 Project code from Intel_Site_Names lookup
    Site            VARCHAR(100)    NOT NULL,       -- Site code (e.g., 'Fab12', 'D1X')
    Category        VARCHAR(100)    NOT NULL,       -- Cost category (e.g., 'All Labor', 'Materials', 'Travel')

    -- Period information
    FiscalYear      INT             NULL,           -- Fiscal year (e.g., 2025) - extracted from ReleaseDate
    Period          INT             NOT NULL,       -- Accounting period (1-12, where 1=Jan, 2=Feb, etc.)

    -- Financial data
    Actuals         DECIMAL(18,2)   NOT NULL,       -- Dollar amount (Budget, Actual, or Forecast)
    Status          VARCHAR(20)     NULL,           -- Data type: 'Actual', 'Budget', or 'Forecast'

    -- Release tracking (CRITICAL for data versioning)
    ReleaseDate     VARCHAR(20)     NULL,           -- Release date in YYYY-MM format (e.g., '2025-03')
    ReportPeriod    INT             NULL,           -- Period when data was reported (1-12)

    -- Primary key ensures unique combination
    CONSTRAINT PK_FY25_Budget_Actuals_DIBS PRIMARY KEY CLUSTERED
    (
        Site        ASC,
        Category    ASC,
        Period      ASC,
        Status      ASC,
        ReleaseDate ASC
    )
);
GO

-- Create indexes for common query patterns
CREATE NONCLUSTERED INDEX IX_Period
    ON dbo.FY25_Budget_Actuals_DIBS (Period ASC);
GO

CREATE NONCLUSTERED INDEX IX_Site
    ON dbo.FY25_Budget_Actuals_DIBS (Site ASC);
GO

CREATE NONCLUSTERED INDEX IX_Status
    ON dbo.FY25_Budget_Actuals_DIBS (Status ASC);
GO

CREATE NONCLUSTERED INDEX IX_ReleaseDate
    ON dbo.FY25_Budget_Actuals_DIBS (ReleaseDate ASC);
GO

CREATE NONCLUSTERED INDEX IX_ReportPeriod
    ON dbo.FY25_Budget_Actuals_DIBS (ReportPeriod ASC);
GO

CREATE NONCLUSTERED INDEX IX_FiscalYear
    ON dbo.FY25_Budget_Actuals_DIBS (FiscalYear ASC);
GO

-- Add column descriptions
EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'L2 Project code mapped from Site via Intel_Site_Names lookup table',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'L2_Proj';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Site identifier code',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'Site';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Cost category (e.g., All Labor, CTM Labor, Site Labor, Overtime, Vacation, Fringe, Subk, Materials, ODCs, Travel, Fee)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'Category';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Fiscal year - extracted from ReleaseDate',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'FiscalYear';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Accounting period (1-12) representing the month the costs are FOR (1=Jan, 2=Feb, etc.)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'Period';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Dollar amount (Budget, Actual, or Forecast value)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'Actuals';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Data type: Actual, Budget, or Forecast',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'Status';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Release date in YYYY-MM format indicating when this data was published (e.g., 2025-03 for March 2025 release)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'ReleaseDate';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Report period (1-12) representing which month the data was REPORTED IN - extracted from ReleaseDate',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS',
    @level2type = N'COLUMN', @level2name = N'ReportPeriod';
GO

-- Table-level description
EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Budget and actual financial data populated by depivot tool. Includes release tracking for data versioning.',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'FY25_Budget_Actuals_DIBS';
GO

PRINT 'Table dbo.FY25_Budget_Actuals_DIBS created successfully!';
PRINT 'Schema: L2_Proj, Site, Category, FiscalYear, Period, Actuals, Status, ReleaseDate, ReportPeriod';
GO

-- ============================================================================
-- Example Queries
-- ============================================================================

-- View table structure
-- EXEC sp_help 'dbo.FY25_Budget_Actuals_DIBS';

-- Get latest release data for P1 Actuals
-- SELECT * FROM dbo.FY25_Budget_Actuals_DIBS
-- WHERE Period = 1 AND Status = 'Actual'
-- AND ReleaseDate = (SELECT MAX(ReleaseDate) FROM dbo.FY25_Budget_Actuals_DIBS);

-- Get P1 Actuals as reported in P3 release (March)
-- SELECT * FROM dbo.FY25_Budget_Actuals_DIBS
-- WHERE Period = 1 AND Status = 'Actual' AND ReportPeriod = 3;

-- Compare Actual vs Budget for a specific period
-- SELECT
--     Site, Category, Period,
--     SUM(CASE WHEN Status = 'Budget' THEN Actuals ELSE 0 END) AS Budget,
--     SUM(CASE WHEN Status = 'Actual' THEN Actuals ELSE 0 END) AS Actual
-- FROM dbo.FY25_Budget_Actuals_DIBS
-- WHERE Period = 1
-- GROUP BY Site, Category, Period;

-- ============================================================================
