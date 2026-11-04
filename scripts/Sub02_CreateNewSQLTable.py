# Title: Creating a new SQL table for storing the FTIR data. 
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/24/2024
# ======================================================================================================================

# Importing the required libraries.
import os
import re
import math
import hashlib
import sqlite3
import numpy as np
import pandas as pd


def Create_SQLite3_DB_Connect(path):
    """
    This function generates a new database and set up the main table in that database. 

    :param path: full path to the database file. 
    :return: connection to the generated database using the sqlite3 library. 
    """
    # Creating the new database file (it is not existed, already checked), and make a connection to the file. 
    conn = sqlite3.connect(path)
    
    # Creating a curser object to execute the sql commands. 
    cursor = conn.cursor()

    # Creating the new table. 
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS FTIR (
        id INTEGER PRIMARY KEY,
        Bnumber INTEGER,
        Lab_Aging TEXT,
        RepNumber INTEGER,
        FileName TEXT,
        FileDirectory TEXT,
        ICO_Baseline REAL,
        ICO_Tangential REAL,
        ISO_Baseline REAL,
        ISO_Tangential REAL,
        Carbonyl_Area_Baseline REAL,
        Carbonyl_Area_Tangential REAL,
        Sulfoxide_Area_Baseline REAL,
        Sulfoxide_Area_Tangential REAL,
        Aliphatic_Area_Baseline REAL,
        Aliphatic_Area_Tangential REAL,
        Carbonyl_Peak_Wavenumber REAL,
        Sulfoxide_Peak_Wavenumber REAL,
        Aliphatic_Peak_Wavenumber_1 REAL,
        Aliphatic_Peak_Wavenumber_2 REAL,
        Carbonyl_Peak_Absorption REAL,
        Sulfoxide_Peak_Absorption REAL,
        Aliphatic_Peak_Absorption_1 REAL,
        Aliphatic_Peak_Absorption_2 REAL,
        Wavenumber BLOB,
        Wavenumber_shape TEXT,
        Wavenumber_dtype TEXT, 
        Absorption BLOB,
        Absorption_shape TEXT,
        Absorption_dtype TEXT,
        RawWavenumber BLOB,
        RawWavenumber_shape TEXT,
        RawWavenumber_dtype TEXT,
        RawAbsorbance BLOB,
        RawAbsorbance_shape TEXT,
        RawAbsorbance_dtype TEXT,
        Carbonyl_Min_Wavenumber REAL,
        Carbonyl_Max_Wavenumber REAL,
        Sulfoxide_Min_Wavenumber REAL,
        Sulfoxide_Max_Wavenumber REAL,
        Aliphatic_Min_Wavenumber REAL,
        Aliphatic_Max_Wavenumber REAL,
        Baseline_Adjustment_Method TEXT,
        ALS_Lambda REAL,
        ALS_Ratio REAL, 
        ALS_NumIter INTEGER,
        Normalization_Method TEXT,
        Normalization_Coeff REAL,
        IsOutlier INTEGER,
        Deconv_ICO REAL, 
        Deconv_ISO REAL, 
        Deconv_GaussianList BLOB,  
        Deconv_GaussianList_shape TEXT,  
        Deconv_GaussianList_dtype TEXT,
        Deconv_CarbonylList BLOB,  
        Deconv_CarbonylList_shape TEXT,  
        Deconv_CarbonylList_dtype TEXT, 
        Deconv_SulfoxideList BLOB, 
        Deconv_SulfoxideList_shape TEXT, 
        Deconv_SulfoxideList_dtype TEXT, 
        Deconv_AliphaticList BLOB, 
        Deconv_AliphaticList_shape TEXT, 
        Deconv_AliphaticList_dtype TEXT          
    )
    """)
    cursor.execute("CREATE INDEX idx_filename ON FTIR (FileName);")       # Creating an index for "FileName"

    # Return the connection.
    return conn, cursor
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


# Columns added to the FTIR table in later versions. A database created before them can still be reviewed, analyzed,
#   plotted, and edited, so it is still opened, with a warning about the features that need these columns.
Older_Version_Columns = ['FileDirectory', 'ALS_Lambda', 'ALS_Ratio', 'ALS_NumIter',
                         'RawWavenumber', 'RawWavenumber_shape', 'RawWavenumber_dtype',
                         'RawAbsorbance', 'RawAbsorbance_shape', 'RawAbsorbance_dtype']


def Check_Database_File(Path, RequireAllColumns=False):
    """
    This function checks if an existing file can be opened as an AutoFTIR database, before actually opening it. The
    expected columns are taken from a temporary database, so they always match what a new database gets. The file is
    opened the same way as the program opens it, since a read-only "file:" URI is rejected on network drives.

    :param Path: full path to the database file.
    :param RequireAllColumns: if True, the columns in "Older_Version_Columns" are required as well.
    :return: an error message if the file cannot be opened (otherwise an empty string), and a warning message if it can
    be opened with limited features (otherwise an empty string).
    """
    FileName = os.path.basename(Path)
    # The rest of the program always adds ".db" to the database name, so another extension would open another file.
    if os.path.splitext(FileName)[1].lower() != '.db':
        return f'"{FileName}" cannot be opened, since AutoFTIR only works with ".db" database files.', ''
    # Get the columns that a new database has.
    TempConn, TempCursor = Create_SQLite3_DB_Connect(':memory:')
    TempCursor.execute("PRAGMA table_info(FTIR)")
    Expected = [Row[1] for Row in TempCursor.fetchall()]
    TempConn.close()
    # Read the tables and columns of the file.
    conn = None
    try:
        conn = sqlite3.connect(Path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        Tables = [Row[0] for Row in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(FTIR)")
        Columns = [Row[1].lower() for Row in cursor.fetchall()]
    except sqlite3.Error as Err:
        return f'"{FileName}" could not be read as a database.\n\n{Err}', ''
    finally:
        if conn is not None:
            conn.close()
    # Check the table.
    if len(Columns) == 0:
        Found = ', '.join(Tables) if len(Tables) > 0 else 'none'
        return f'"{FileName}" has no table named "FTIR", which AutoFTIR needs.\n\nTables in this file: {Found}', ''
    # Check the columns.
    Missing = [Name for Name in Expected if Name.lower() not in Columns]
    MissingNeeded = [Name for Name in Missing if RequireAllColumns or Name not in Older_Version_Columns]
    if len(MissingNeeded) > 0:
        Shown = ', '.join(MissingNeeded[:10])
        if len(MissingNeeded) > 10:
            Shown += f', and {len(MissingNeeded) - 10} more'
        return f'The "FTIR" table in "{FileName}" is missing {len(MissingNeeded)} column(s) that AutoFTIR needs.\n\n' \
               f'Missing: {Shown}', ''
    if len(Missing) > 0:
        return '', (f'"{FileName}" was created by an older version of AutoFTIR, and is missing these columns: '
                    f'{", ".join(Missing)}.\n\nYou can still review, analyze, plot, and edit its records. However, '
                    f'adding data, modifying a record, "Export Individual Record", and "Export Database (Summary)" '
                    f'will not work on this database, and can close the program.')
    return '', ''
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_DB_SummaryData(cursor):
    """
    This function goes through the Database and tries to extract the summary information.

    :param cursor: cursor for executing the SQL commands. 
    :return: a dictionary of the summary information. 
    """
    # First, get the total number of data. 
    cursor.execute("SELECT COUNT(*) FROM FTIR")
    NumRows = cursor.fetchone()[0]
    # Get the total number of data, excluding outliers. 
    cursor.execute("SELECT COUNT(*) FROM FTIR WHERE IsOutlier = ?", (0,))
    NumValidRows = cursor.fetchone()[0]
    # Get the number of unique B-numbers.
    cursor.execute("SELECT COUNT(DISTINCT Bnumber) FROM FTIR WHERE IsOutlier = ?", (0,))
    NumUniqueBnumber = cursor.fetchone()[0]
    # Get the number of unique Lab aging conditions.
    cursor.execute("SELECT COUNT(DISTINCT Lab_Aging) FROM FTIR WHERE IsOutlier = ?", (0,))
    NumUniqueLabAging = cursor.fetchone()[0]
    # Get the number of unique B-number and aging combinations. 
    cursor.execute("SELECT COUNT(*) FROM (SELECT DISTINCT Bnumber, Lab_Aging FROM FTIR)")
    NumUniqueBnumLabAge = cursor.fetchone()[0]
    # Get average number of replicates per each sample. 
    try:
        AvgNumReplicates = NumValidRows / NumUniqueBnumLabAge
    except:
        AvgNumReplicates = -1
    
    # Return the extracted information. 
    return {
        'NumRows': NumRows,
        'NumValidRows': NumValidRows,
        'NumUniqueBnumber': NumUniqueBnumber,
        'NumUniqueLabAging': NumUniqueLabAging,
        'NumUniqueBnumLabAge': NumUniqueBnumLabAge,
        'AvgNumRep': AvgNumReplicates
    }
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Append_to_Database(conn, cursor, data):
    """
    This function adds data as new row to the database. 
    """
    # Add the data using execute command. 
    # Insert data into the table
    cursor.execute("""
    INSERT INTO FTIR (
        Bnumber, Lab_Aging, RepNumber, FileName, FileDirectory,
        ICO_Baseline, ICO_Tangential, ISO_Baseline, ISO_Tangential,
        Carbonyl_Area_Baseline, Carbonyl_Area_Tangential, Sulfoxide_Area_Baseline, Sulfoxide_Area_Tangential,
        Aliphatic_Area_Baseline, Aliphatic_Area_Tangential,
        Carbonyl_Peak_Wavenumber, Sulfoxide_Peak_Wavenumber, Aliphatic_Peak_Wavenumber_1, Aliphatic_Peak_Wavenumber_2,
        Carbonyl_Peak_Absorption, Sulfoxide_Peak_Absorption, Aliphatic_Peak_Absorption_1, Aliphatic_Peak_Absorption_2,
        Wavenumber, Wavenumber_shape, Wavenumber_dtype,
        Absorption, Absorption_shape, Absorption_dtype,
        RawWavenumber, RawWavenumber_shape, RawWavenumber_dtype,
        RawAbsorbance, RawAbsorbance_shape, RawAbsorbance_dtype,
        Carbonyl_Min_Wavenumber, Carbonyl_Max_Wavenumber,
        Sulfoxide_Min_Wavenumber, Sulfoxide_Max_Wavenumber,
        Aliphatic_Min_Wavenumber, Aliphatic_Max_Wavenumber,
        Baseline_Adjustment_Method, ALS_Lambda, ALS_Ratio, ALS_NumIter,
        Normalization_Method, Normalization_Coeff, IsOutlier, 
        Deconv_ICO, Deconv_ISO, 
        Deconv_GaussianList,  Deconv_GaussianList_shape,  Deconv_GaussianList_dtype,
        Deconv_CarbonylList,  Deconv_CarbonylList_shape,  Deconv_CarbonylList_dtype, 
        Deconv_SulfoxideList, Deconv_SulfoxideList_shape, Deconv_SulfoxideList_dtype, 
        Deconv_AliphaticList, Deconv_AliphaticList_shape, Deconv_AliphaticList_dtype
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
               ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    """, (
        data["Bnumber"], data["Lab_Aging"], data["RepNumber"], data["FileName"], data["FileDirectory"],
        data["ICO_Baseline"], data["ICO_Tangential"], data["ISO_Baseline"], data["ISO_Tangential"],
        data["Carbonyl_Area_Baseline"], data["Carbonyl_Area_Tangential"],
        data["Sulfoxide_Area_Baseline"], data["Sulfoxide_Area_Tangential"],
        data["Aliphatic_Area_Baseline"], data["Aliphatic_Area_Tangential"],
        data["Carbonyl_Peak_Wavenumber"], data["Sulfoxide_Peak_Wavenumber"],
        data["Aliphatic_Peak_Wavenumber_1"], data["Aliphatic_Peak_Wavenumber_2"],
        data["Carbonyl_Peak_Absorption"], data["Sulfoxide_Peak_Absorption"],
        data["Aliphatic_Peak_Absorption_1"], data["Aliphatic_Peak_Absorption_2"],
        data["Wavenumber"], data["Wavenumber_shape"], data["Wavenumber_dtype"],
        data["Absorption"], data["Absorption_shape"], data["Absorption_dtype"],
        data["RawWavenumber"], data["RawWavenumber_shape"], data["RawWavenumber_dtype"],
        data["RawAbsorbance"], data["RawAbsorbance_shape"], data["RawAbsorbance_dtype"],
        data["Carbonyl_Min_Wavenumber"], data["Carbonyl_Max_Wavenumber"],
        data["Sulfoxide_Min_Wavenumber"], data["Sulfoxide_Max_Wavenumber"],
        data["Aliphatic_Min_Wavenumber"], data["Aliphatic_Max_Wavenumber"],
        data["Baseline_Adjustment_Method"], data["ALS_Lambda"], data["ALS_Ratio"], data["ALS_NumIter"],
        data["Normalization_Method"], data["Normalization_Coeff"], data["IsOutlier"], 
        data["Deconv_ICO"], data["Deconv_ISO"],
        data["Deconv_GaussianList"],  data["Deconv_GaussianList_shape"],  data["Deconv_GaussianList_dtype"],
        data["Deconv_CarbonylList"],  data["Deconv_CarbonylList_shape"],  data["Deconv_CarbonylList_dtype"], 
        data["Deconv_SulfoxideList"], data["Deconv_SulfoxideList_shape"], data["Deconv_SulfoxideList_dtype"], 
        data["Deconv_AliphaticList"], data["Deconv_AliphaticList_shape"], data["Deconv_AliphaticList_dtype"]
    ))

    # Commit the changes. 
    conn.commit()

    # Return Nothing. 
    return 
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Update_Row_in_Database(conn, cursor, idx, data):
    """
    This function adds data as new row to the database. 
    """
    # Add the data using execute command. 
    # Insert data into the table
    cursor.execute("""
    UPDATE FTIR
    SET 
         ICO_Baseline = ?, ICO_Tangential = ?, ISO_Baseline = ?, ISO_Tangential = ?,
         Carbonyl_Area_Baseline = ?, Carbonyl_Area_Tangential = ?, 
         Sulfoxide_Area_Baseline = ?, Sulfoxide_Area_Tangential = ?,
         Aliphatic_Area_Baseline = ?, Aliphatic_Area_Tangential = ?,
         Carbonyl_Peak_Wavenumber = ?, Sulfoxide_Peak_Wavenumber = ?, 
         Aliphatic_Peak_Wavenumber_1 = ?, Aliphatic_Peak_Wavenumber_2 = ?,
         Carbonyl_Peak_Absorption = ?, Sulfoxide_Peak_Absorption = ?, 
         Aliphatic_Peak_Absorption_1 = ?, Aliphatic_Peak_Absorption_2 = ?,
         Carbonyl_Min_Wavenumber = ?, Carbonyl_Max_Wavenumber = ?,
         Sulfoxide_Min_Wavenumber = ?, Sulfoxide_Max_Wavenumber = ?,
         Aliphatic_Min_Wavenumber = ?, Aliphatic_Max_Wavenumber = ?,
         Deconv_CarbonylList = ?, Deconv_CarbonylList_shape = ?, Deconv_CarbonylList_dtype = ?, 
         Deconv_SulfoxideList = ?, Deconv_SulfoxideList_shape = ?, Deconv_SulfoxideList_dtype = ?, 
         Deconv_AliphaticList = ?, Deconv_AliphaticList_shape = ?, Deconv_AliphaticList_dtype = ?, 
         Deconv_GaussianList = ?, Deconv_GaussianList_shape = ?, Deconv_GaussianList_dtype = ?,
         Deconv_ICO = ?, Deconv_ISO = ?, 
         ALS_Lambda = ?, ALS_Ratio = ?, ALS_NumIter = ?, Normalization_Method = ?, Normalization_Coeff = ?, 
         Wavenumber = ?, Wavenumber_shape = ?, Wavenumber_dtype = ?,
         Absorption = ?, Absorption_shape = ?, Absorption_dtype = ?,
         IsOutlier = ? 
    WHERE id = ?
    """, (
        data["ICO_Baseline"], data["ICO_Tangential"], data["ISO_Baseline"], data["ISO_Tangential"],
        data["Carbonyl_Area_Baseline"], data["Carbonyl_Area_Tangential"],
        data["Sulfoxide_Area_Baseline"], data["Sulfoxide_Area_Tangential"],
        data["Aliphatic_Area_Baseline"], data["Aliphatic_Area_Tangential"],
        data["Carbonyl_Peak_Wavenumber"], data["Sulfoxide_Peak_Wavenumber"],
        data["Aliphatic_Peak_Wavenumber_1"], data["Aliphatic_Peak_Wavenumber_2"],
        data["Carbonyl_Peak_Absorption"], data["Sulfoxide_Peak_Absorption"],
        data["Aliphatic_Peak_Absorption_1"], data["Aliphatic_Peak_Absorption_2"],
        data["Carbonyl_Min_Wavenumber"], data["Carbonyl_Max_Wavenumber"],
        data["Sulfoxide_Min_Wavenumber"], data["Sulfoxide_Max_Wavenumber"],
        data["Aliphatic_Min_Wavenumber"], data["Aliphatic_Max_Wavenumber"],
        data["Decon_Carbonyl"], data["Decon_Carbonyl_shape"], data["Decon_Carbonyl_dtype"],
        data["Decon_Sulfoxide"], data["Decon_Sulfoxide_shape"], data["Decon_Sulfoxide_dtype"],
        data["Decon_Aliphatic"], data["Decon_Aliphatic_shape"], data["Decon_Aliphatic_dtype"], 
        data["Decon_GaussianList"], data["Decon_GaussianList_shape"], data["Decon_GaussianList_dtype"], 
        data["Decon_ICO"], data["Decon_ISO"], 
        data["ALS_Lambda"], data["ALS_Ratio"], data["ALS_NumIter"], 
        data["Normalization_Method"], data["Normalization_Coeff"],
        data["Wavenumber"], data["Wavenumber_shape"], data["Wavenumber_dtype"],
        data["Absorption"], data["Absorption_shape"], data["Absorption_dtype"],
        data["IsOutlier"], idx
    ))

    # Commit the changes. 
    conn.commit()

    # Return Nothing. 
    return 
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Info_From_Name(FileName):
    """
    This function tries to extract the B-number, sample repetition number, and lag aging levels. It is noted that the 
    file should have the following structure, or it will not be considered. 
    "BXXX_FTIR_RepY_ZZZ.dpt"

    :param FileName: String of the file name. 
    :return: B-number, Repetition number, and lab aging condition. 
    """
    # Get the file name without the extension. 
    fnameNoExt = os.path.splitext(FileName)[0] + '.'
    # Write the function using the regular expression. 
    try:
        Pattern1 = re.compile(r"^B(?P<Bnumber>\d{4,5})_FTIR_Rep(?P<RepNumber>\d+)_(?P<Aging>[A-Za-z0-9]+)\.")
        Pattern2 = re.compile(r"^B(?P<Bnumber>\d{4,5})_FTIR_(?P<RepNumber>\d+)_(?P<Aging>[A-Za-z0-9]+)\.")
        Match = Pattern1.match(fnameNoExt) or Pattern2.match(fnameNoExt)
        if not Match:
            raise Exception(f"File name not following pre-determined patterns!")
        # Extract groups
        Bnumber = int(Match.group("Bnumber"))
        Rep = int(Match.group("RepNumber"))
        Aging = Match.group("Aging").upper()
    except:
        return None, None, None
    # Return the results.
    return Bnumber, Rep, Aging
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Identifier_Combinations(cursor):
    """
    This function fetch all combinations of the B-number, Lab aging, and repetition numbers from the database. 

    :param cursor: cursor for executing the SQLite3 commands. 
    """
    # First, query for all combinations.
    cursor.execute("SELECT DISTINCT Bnumber, Lab_Aging, RepNumber FROM FTIR")
    Combinations = cursor.fetchall()
    # Convert the available combinations to the dataframe.
    Combinations = pd.DataFrame(Combinations, columns=["Bnumber", "Lab_Aging", "RepNumber"])
    Combinations = Combinations.sort_values(by='Bnumber', ascending=True)
    Combinations['Bnumber'] = Combinations['Bnumber'].astype(str)
    # Return the combinations DF as result.
    return Combinations
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Unique_Aging_Levels(cursor):
    """
    This function returns the sorted list of unique lab aging levels currently available in the database.

    :param cursor: cursor for executing the SQLite3 commands.
    :return: list of the unique aging level names.
    """
    cursor.execute("SELECT DISTINCT Lab_Aging FROM FTIR WHERE Lab_Aging IS NOT NULL AND Lab_Aging != '' "
                   "ORDER BY Lab_Aging")
    return [Row[0] for Row in cursor.fetchall()]
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Is_Valid_Aging_Name(Name):
    """
    This function checks a new aging level name: English letters and numbers only, starting with a letter.

    :param Name: the aging level name to be checked.
    :return: True if the name is valid, False otherwise.
    """
    return re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", Name) is not None
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Has_Original_Aging_Column(cursor):
    """
    This function checks if the "AgingLevel_Original" backup column was already added to the FTIR table.

    :param cursor: cursor for executing the SQLite3 commands.
    :return: True if the column exists, False otherwise.
    """
    cursor.execute("PRAGMA table_info(FTIR)")
    return 'AgingLevel_Original' in [Row[1] for Row in cursor.fetchall()]
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Count_Aging_Collisions(cursor, OldLevel, NewLevel):
    """
    This function counts the records that would share the same B-number, repetition number, and aging level with an
    existing record, if "OldLevel" were renamed to the already available "NewLevel".

    :param cursor: cursor for executing the SQLite3 commands.
    :param OldLevel: the aging level to be renamed.
    :param NewLevel: the new aging level name.
    :return: number of the colliding records.
    """
    cursor.execute("""
    SELECT COUNT(*) FROM FTIR AS A JOIN FTIR AS B ON A.Bnumber = B.Bnumber AND A.RepNumber = B.RepNumber
    WHERE A.Lab_Aging = ? AND B.Lab_Aging = ?
    """, (OldLevel, NewLevel))
    return cursor.fetchone()[0]
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Available_Rep_Number(cursor, Bnumber, LabAging, CurrentRep, RecordID):
    """
    This function finds the repetition number of a record at a B-number and aging level. The record keeps its current
    number if no other record is using it. Otherwise, it gets the number after the largest one in use, so a number
    missing from the list (e.g., of a deleted record) is not reused. Gaps in the numbers are fine, since the analysis
    only counts the records of each B-number and aging level.

    :param cursor: cursor for executing the SQLite3 commands.
    :param Bnumber: the B-number of the record.
    :param LabAging: the aging level of the record.
    :param CurrentRep: the current repetition number of the record.
    :param RecordID: the "id" of the record, which is excluded from the search.
    :return: the repetition number to be used.
    """
    cursor.execute("SELECT RepNumber FROM FTIR WHERE Bnumber = ? AND Lab_Aging = ? AND id != ? "
                   "AND RepNumber IS NOT NULL", (Bnumber, LabAging, RecordID))
    UsedReps = [Row[0] for Row in cursor.fetchall()]
    return CurrentRep if CurrentRep not in UsedReps else max(UsedReps) + 1
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Backup_Original_Identifiers(cursor):
    """
    This function copies the current aging level, B-number, and repetition number of every record without a backup to
    the "AgingLevel_Original", "Bnumber_Original", and "RepNumber_Original" columns (which are created if needed), so a
    record's backup always keeps its very first values. The repetition number is included since it can change
    automatically with the others (see "Get_Available_Rep_Number"). The caller is responsible for the transaction.

    :param cursor: cursor for executing the SQLite3 commands.
    """
    cursor.execute("PRAGMA table_info(FTIR)")
    Columns = [Row[1] for Row in cursor.fetchall()]
    if 'AgingLevel_Original' not in Columns:
        cursor.execute("ALTER TABLE FTIR ADD COLUMN AgingLevel_Original TEXT DEFAULT ''")
    if 'Bnumber_Original' not in Columns:
        cursor.execute("ALTER TABLE FTIR ADD COLUMN Bnumber_Original INTEGER")
    if 'RepNumber_Original' not in Columns:
        cursor.execute("ALTER TABLE FTIR ADD COLUMN RepNumber_Original INTEGER")
    cursor.execute("UPDATE FTIR SET AgingLevel_Original = Lab_Aging "
                   "WHERE AgingLevel_Original IS NULL OR AgingLevel_Original = ''")
    cursor.execute("UPDATE FTIR SET Bnumber_Original = Bnumber WHERE Bnumber_Original IS NULL")
    cursor.execute("UPDATE FTIR SET RepNumber_Original = RepNumber WHERE RepNumber_Original IS NULL")
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Rename_Aging_Level(conn, cursor, OldLevel, NewLevel):
    """
    This function renames an aging level on all of its records, after backing up the identifiers (see
    "Backup_Original_Identifiers"). Everything is done in a single transaction, so a failure leaves the database
    unchanged.

    :param conn: connection to the database.
    :param cursor: cursor for executing the SQLite3 commands.
    :param OldLevel: the aging level to be renamed.
    :param NewLevel: the new aging level name.
    :return: number of the renamed records.
    """
    if not conn.in_transaction:
        cursor.execute("BEGIN")
    try:
        Backup_Original_Identifiers(cursor)
        cursor.execute("UPDATE FTIR SET Lab_Aging = ? WHERE Lab_Aging = ?", (NewLevel, OldLevel))
        NumRenamed = cursor.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return NumRenamed
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Update_Record_Identifiers(conn, cursor, RecordID, Bnumber, LabAging):
    """
    This function changes the B-number and aging level of a single record, and updates its repetition number if needed
    (see "Get_Available_Rep_Number"), after backing up the identifiers (see "Backup_Original_Identifiers"). The file
    name is kept as it is, since it is what detects a file already loaded in the database. Everything is done in a
    single transaction, so a failure leaves the database unchanged.

    :param conn: connection to the database.
    :param cursor: cursor for executing the SQLite3 commands.
    :param RecordID: the "id" of the record to be changed.
    :param Bnumber: the new B-number.
    :param LabAging: the new aging level.
    :return: the repetition number of the record after the change.
    """
    cursor.execute("SELECT RepNumber FROM FTIR WHERE id = ?", (RecordID,))
    OldRep = cursor.fetchone()[0]
    NewRep = Get_Available_Rep_Number(cursor, Bnumber, LabAging, OldRep, RecordID)
    if not conn.in_transaction:
        cursor.execute("BEGIN")
    try:
        Backup_Original_Identifiers(cursor)
        cursor.execute("UPDATE FTIR SET Bnumber = ?, Lab_Aging = ?, RepNumber = ? WHERE id = ?",
                       (Bnumber, LabAging, NewRep, RecordID))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return NewRep
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Count_Modified_Aging_Records(cursor):
    """
    This function counts the records whose aging level differs from their backup in "AgingLevel_Original". Records with
    an empty backup were added after the last rename, so their current aging level is still their original one.

    :param cursor: cursor for executing the SQLite3 commands.
    :return: number of the modified records (zero if the backup column does not exist).
    """
    if not Has_Original_Aging_Column(cursor):
        return 0
    cursor.execute("SELECT COUNT(*) FROM FTIR WHERE AgingLevel_Original IS NOT NULL AND AgingLevel_Original != '' "
                   "AND Lab_Aging IS NOT AgingLevel_Original")
    return cursor.fetchone()[0]
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Restore_Original_Aging_Levels(conn, cursor):
    """
    This function copies the "AgingLevel_Original" backup back to the aging level column. Records with an empty backup
    are skipped, since copying it would erase their aging level (see "Count_Modified_Aging_Records"). A restored record
    whose repetition number is already taken at its original aging level gets a new one (see
    "Get_Available_Rep_Number"), which is checked after all records are restored, so that records only trading places
    are left unchanged.

    :param conn: connection to the database.
    :param cursor: cursor for executing the SQLite3 commands.
    :return: number of the restored records, and how many of them got a new repetition number.
    """
    Condition = "AgingLevel_Original IS NOT NULL AND AgingLevel_Original != '' AND Lab_Aging IS NOT AgingLevel_Original"
    if not conn.in_transaction:
        cursor.execute("BEGIN")
    try:
        cursor.execute(f"SELECT id FROM FTIR WHERE {Condition}")
        RestoredIDs = [Row[0] for Row in cursor.fetchall()]
        Backup_Original_Identifiers(cursor)
        cursor.execute(f"UPDATE FTIR SET Lab_Aging = AgingLevel_Original WHERE {Condition}")
        NumRenumbered = Renumber_Restored_Records(cursor, RestoredIDs)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return len(RestoredIDs), NumRenumbered
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Renumber_Restored_Records(cursor, RestoredIDs):
    """
    This function gives a new repetition number to the restored records whose number is already taken (see
    "Get_Available_Rep_Number"). The caller is responsible for the transaction.

    :param cursor: cursor for executing the SQLite3 commands.
    :param RestoredIDs: list of the "id" of the restored records.
    :return: number of the records that got a new repetition number.
    """
    NumRenumbered = 0
    for RecordID in RestoredIDs:
        cursor.execute("SELECT Bnumber, Lab_Aging, RepNumber FROM FTIR WHERE id = ?", (RecordID,))
        Bnumber, LabAging, Rep = cursor.fetchone()
        NewRep = Get_Available_Rep_Number(cursor, Bnumber, LabAging, Rep, RecordID)
        if NewRep != Rep:
            cursor.execute("UPDATE FTIR SET RepNumber = ? WHERE id = ?", (NewRep, RecordID))
            NumRenumbered += 1
    return NumRenumbered
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Count_Modified_Identifier_Records(cursor):
    """
    This function counts the records whose aging level, B-number, or repetition number differs from its backup. Records
    with an empty backup still have their original value. A database may not have all backup columns yet, if its aging
    levels were changed by an earlier version of the program.

    :param cursor: cursor for executing the SQLite3 commands.
    :return: number of the modified records (zero if no backup column exists).
    """
    cursor.execute("PRAGMA table_info(FTIR)")
    Columns = [Row[1] for Row in cursor.fetchall()]
    Conditions = []
    if 'AgingLevel_Original' in Columns:
        Conditions.append("(AgingLevel_Original IS NOT NULL AND AgingLevel_Original != '' "
                          "AND Lab_Aging IS NOT AgingLevel_Original)")
    if 'Bnumber_Original' in Columns:
        Conditions.append("(Bnumber_Original IS NOT NULL AND Bnumber IS NOT Bnumber_Original)")
    if 'RepNumber_Original' in Columns:
        Conditions.append("(RepNumber_Original IS NOT NULL AND RepNumber IS NOT RepNumber_Original)")
    if len(Conditions) == 0:
        return 0
    cursor.execute(f"SELECT COUNT(*) FROM FTIR WHERE {' OR '.join(Conditions)}")
    return cursor.fetchone()[0]
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Restore_Original_Identifiers(conn, cursor):
    """
    This function copies the backups of the aging level, B-number, and repetition number back to their columns. The
    backups are first filled for the records without one, so those records keep their current values. A restored record
    whose repetition number is already taken gets a new one (see "Renumber_Restored_Records"), which is checked after
    all records are restored, so that records only trading places are left unchanged. Everything is done in a single
    transaction, so a failure leaves the database unchanged.

    :param conn: connection to the database.
    :param cursor: cursor for executing the SQLite3 commands.
    :return: number of the restored records, and how many of them got a new repetition number.
    """
    Condition = ("Lab_Aging IS NOT AgingLevel_Original OR Bnumber IS NOT Bnumber_Original "
                 "OR RepNumber IS NOT RepNumber_Original")
    if not conn.in_transaction:
        cursor.execute("BEGIN")
    try:
        Backup_Original_Identifiers(cursor)
        cursor.execute(f"SELECT id FROM FTIR WHERE {Condition}")
        RestoredIDs = [Row[0] for Row in cursor.fetchall()]
        cursor.execute(f"UPDATE FTIR SET Lab_Aging = AgingLevel_Original, Bnumber = Bnumber_Original, "
                       f"RepNumber = RepNumber_Original WHERE {Condition}")
        NumRenumbered = Renumber_Restored_Records(cursor, RestoredIDs)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return len(RestoredIDs), NumRenumbered
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Find_Common_Records(SourcePaths):
    """
    This function finds the common records of several databases, meaning the B-number, aging level, and repetition
    number combinations available in two or more of the databases. A combination repeated only inside one database is
    not included, since there is no choice between databases to make for it.

    :param SourcePaths: list of the full paths to the databases.
    :return: A dictionary of each common combination (B-number, aging level, repetition number) with a list of
    (index in "SourcePaths", deconvolution ICO, deconvolution ISO) for each database that has it, in the order of
    "SourcePaths", and the total number of records with these combinations. The values are from the first record of that
    combination in the database, which is the one that would be kept, and are None if not available (see
    "Get_Deconv_Value").
    """
    Found = {}
    for Index, Path in enumerate(SourcePaths):
        if not os.path.isfile(Path):                # Connecting to a missing file would create it.
            raise FileNotFoundError(f'"{Path}" was not found.')
        Source = sqlite3.connect(Path)
        try:
            for Bnumber, LabAging, Rep, ICO, ISO, IsOutlier in Source.execute(
                    "SELECT Bnumber, Lab_Aging, RepNumber, Deconv_ICO, Deconv_ISO, IsOutlier FROM FTIR ORDER BY id"):
                Found.setdefault((Bnumber, LabAging, Rep), []).append(
                    (Index, Get_Deconv_Value(ICO, IsOutlier), Get_Deconv_Value(ISO, IsOutlier)))
        finally:
            Source.close()
    Common = {}
    for Record, Entries in Found.items():
        FirstEntries = {}
        for Entry in Entries:
            FirstEntries.setdefault(Entry[0], Entry)
        if len(FirstEntries) > 1:
            Common[Record] = [FirstEntries[Index] for Index in sorted(FirstEntries)]
    return Common, sum(len(Found[Record]) for Record in Common)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Deconv_Value(Value, IsOutlier):
    """
    This function returns a deconvolution ICO or ISO value of a record, or None if it is not available. An outlier record
    has no valid value, and is saved with -1 for them.

    :param Value: the value from the database.
    :param IsOutlier: the "IsOutlier" value of the record.
    :return: the value, or None.
    """
    if IsOutlier or not isinstance(Value, (int, float)) or math.isnan(Value) or Value < 0:
        return None
    return Value
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Merge_Databases(SourcePaths, OutputPath, progress_callback=None, KeepFrom=None):
    """
    This function merges the records of several databases into a new database, without changing the source databases.
    Records get new "id" values, and in the order of "SourcePaths":
      - For a combination in "KeepFrom", only one record is merged: the first one of the selected database.
      - Any other record with the same file name and the same raw spectrum as an earlier record is the same test, so it
        is skipped. Keeping both would count one test as two replicates in the analysis.
      - Other records keep their repetition number if it is free, and otherwise get a new one, saved in their backup
        (see "Get_Available_Rep_Number" and "Backup_Original_Identifiers").
      - Any extra columns of the sources (such as the backup columns) are kept.
    The new database is built in a temporary file and only gets its final name at the end, so a failure never leaves a
    partial database behind.

    :param SourcePaths: list of the full paths to the databases to be merged.
    :param OutputPath: full path to the new database, which must not exist.
    :param progress_callback: Optional callable(NumProcessed, Total) invoked for each source record.
    :param KeepFrom: Optional dictionary of the common combinations (see "Find_Common_Records"), with the index in
    "SourcePaths" of the database to keep them from.
    :return: A dictionary with the number of merged records ("NumRecords"), common records left out ("NumCommon"), skipped
    records ("NumSkipped"), and merged records that got a new repetition number ("NumRenumbered").
    """
    KeepFrom = {} if KeepFrom is None else KeepFrom
    if os.path.exists(OutputPath):
        raise FileExistsError(f'"{OutputPath}" already exists.')
    # Check all sources before starting. They may have changed since they were selected.
    Total = 0
    for Path in SourcePaths:
        if not os.path.isfile(Path):                # Connecting to a missing file would create it.
            raise FileNotFoundError(f'"{Path}" was not found.')
        Error, _ = Check_Database_File(Path, RequireAllColumns=True)
        if Error:
            raise ValueError(Error)
        Source = sqlite3.connect(Path)
        Total += Source.execute("SELECT COUNT(*) FROM FTIR").fetchone()[0]
        Source.close()
    # Build the new database.
    TempPath = OutputPath + '.merging'
    if os.path.exists(TempPath):                    # Left from a merge that was interrupted.
        os.remove(TempPath)
    conn, cursor = Create_SQLite3_DB_Connect(TempPath)
    Summary = {'NumRecords': 0, 'NumCommon': 0, 'NumSkipped': 0, 'NumRenumbered': 0}
    Seen = set()
    KeptCommon = set()
    NumProcessed = 0
    try:
        for SourceIndex, Path in enumerate(SourcePaths):
            Source = sqlite3.connect(Path)
            try:
                SourceCursor = Source.cursor()
                # Add the extra columns of this source to the new database.
                SourceCursor.execute("PRAGMA table_info(FTIR)")
                ColumnInfo = [(Row[1], Row[2]) for Row in SourceCursor.fetchall() if Row[1].lower() != 'id']
                cursor.execute("PRAGMA table_info(FTIR)")
                Existing = [Row[1].lower() for Row in cursor.fetchall()]
                for Name, Type in ColumnInfo:
                    if Name.lower() not in Existing:
                        cursor.execute(f"ALTER TABLE FTIR ADD COLUMN [{Name}] {Type}")
                # Copy the records.
                Names = [Name for Name, _ in ColumnInfo]
                Position = {Name.lower(): i for i, Name in enumerate(Names)}
                ColumnList = ', '.join(f'[{Name}]' for Name in Names)
                Insert = f"INSERT INTO FTIR ({ColumnList}) VALUES ({', '.join('?' * len(Names))})"
                SourceCursor.execute(f"SELECT {ColumnList} FROM FTIR ORDER BY id")
                for Row in SourceCursor:
                    NumProcessed += 1
                    if progress_callback is not None:
                        progress_callback(NumProcessed, Total)
                    Bnumber, LabAging, Rep = Row[Position['bnumber']], Row[Position['lab_aging']], Row[Position['repnumber']]
                    # Keep only one record of a common combination: the first one of the selected database.
                    Record = (Bnumber, LabAging, Rep)
                    if KeepFrom.get(Record, SourceIndex) != SourceIndex or Record in KeptCommon:
                        Summary['NumCommon'] += 1
                        continue
                    if Record in KeepFrom:
                        KeptCommon.add(Record)
                    # Skip the same test, unless this record was selected for being a common one.
                    RawX, RawY = Row[Position['rawwavenumber']], Row[Position['rawabsorbance']]
                    if isinstance(RawX, bytes) and isinstance(RawY, bytes):
                        Key = (Row[Position['filename']], hashlib.md5(RawX + RawY).hexdigest())
                        if Key in Seen and Record not in KeepFrom:
                            Summary['NumSkipped'] += 1
                            continue
                        Seen.add(Key)
                    # Add the record, and change its repetition number if needed.
                    NewRep = Get_Available_Rep_Number(cursor, Bnumber, LabAging, Rep, -1)
                    cursor.execute(Insert, Row)
                    NewID = cursor.lastrowid
                    if NewRep != Rep:
                        Backup_Original_Identifiers(cursor)
                        cursor.execute("UPDATE FTIR SET RepNumber = ? WHERE id = ?", (NewRep, NewID))
                        Summary['NumRenumbered'] += 1
                    Summary['NumRecords'] += 1
            finally:
                Source.close()
        conn.commit()
    except Exception:
        conn.close()
        os.remove(TempPath)
        raise
    conn.close()
    os.rename(TempPath, OutputPath)
    return Summary
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Recalculate_Indices(conn, cursor, progress_callback=None):
    """
    This function goes through every non-outlier record of the database and recalculates the Carbonyl, Sulfoxide, and
    Aliphatic areas, together with the corresponding ICO/ISO indices, for the Baseline, Tangential, and Deconvolution
    methods, using the spectrum, peak boundaries, and Gaussian fits already stored for that record. It does NOT re-run
    the ALS baseline correction, peak detection, or Gaussian fitting; it only recomputes the derived areas/indices from
    whatever is currently saved, so that records left inconsistent by an interrupted editing/saving flow (e.g., a
    manually edited Gaussian table whose indices weren't fully persisted) get repaired. Records marked as outliers
    (IsOutlier = 1) are skipped and left untouched, consistent with the rest of the program treating outliers as
    excluded from analysis.

    :param conn: Connection to the SQL database.
    :param cursor: cursor for executing the SQL commands.
    :param progress_callback: Optional callable(NumProcessed, NumRows) invoked after each row is processed (whether
    updated, skipped, or errored), for reporting progress to the caller.
    :return: A dictionary summary, including the total number of rows, number of rows updated, number of rows skipped
    (outliers or errors), and a list of (id, error message) tuples for the rows that raised an error.
    """
    # Importing locally to avoid a module-level circular dependency between Sub02 and Sub04.
    from scripts.Sub04_FTIR_Analysis_Functions import Binary_to_Array
    # Fetch everything needed to recompute the areas/indices for all records.
    Columns = [
        'id', 'IsOutlier',
        'Wavenumber', 'Wavenumber_shape', 'Wavenumber_dtype',
        'Absorption', 'Absorption_shape', 'Absorption_dtype',
        'Carbonyl_Min_Wavenumber',  'Carbonyl_Max_Wavenumber',
        'Sulfoxide_Min_Wavenumber', 'Sulfoxide_Max_Wavenumber',
        'Aliphatic_Min_Wavenumber', 'Aliphatic_Max_Wavenumber',
        'Deconv_CarbonylList',  'Deconv_CarbonylList_shape',  'Deconv_CarbonylList_dtype',
        'Deconv_SulfoxideList', 'Deconv_SulfoxideList_shape', 'Deconv_SulfoxideList_dtype',
        'Deconv_AliphaticList', 'Deconv_AliphaticList_shape', 'Deconv_AliphaticList_dtype']
    cursor.execute(f"SELECT {', '.join(Columns)} FROM FTIR")
    Rows = cursor.fetchall()
    NumRows = len(Rows)
    NumUpdated, NumSkipped, Errors = 0, 0, []
    # Iterate over every record.
    for i, row in enumerate(Rows):
        Data = dict(zip(Columns, row))
        ID = Data['id']
        if Data['IsOutlier']:
            # Skip the outlier records, leave their stored values untouched.
            NumSkipped += 1
            if progress_callback: progress_callback(i + 1, NumRows)
            continue
        try:
            # Decode the pre-processed spectrum.
            X = Binary_to_Array(Data['Wavenumber'], Data['Wavenumber_shape'], Data['Wavenumber_dtype'])
            Y = Binary_to_Array(Data['Absorption'], Data['Absorption_shape'], Data['Absorption_dtype'])
            # ----------------------------------------------------------------------------------------------------------
            # Recompute the Baseline and Tangential areas/indices, using the stored peak boundaries.
            CIndex = np.where((X >= Data['Carbonyl_Min_Wavenumber'])  & (X <= Data['Carbonyl_Max_Wavenumber']))[0]
            SIndex = np.where((X >= Data['Sulfoxide_Min_Wavenumber']) & (X <= Data['Sulfoxide_Max_Wavenumber']))[0]
            AIndex = np.where((X >= Data['Aliphatic_Min_Wavenumber']) & (X <= Data['Aliphatic_Max_Wavenumber']))[0]
            CArea_base = np.trapz(Y[CIndex], X[CIndex])
            SArea_base = np.trapz(Y[SIndex], X[SIndex])
            AArea_base = np.trapz(Y[AIndex], X[AIndex])
            CArea_tang = CArea_base - np.abs(X[CIndex[0]] - X[CIndex[-1]]) * Y[CIndex[[0, -1]]].mean()
            SArea_tang = SArea_base - np.abs(X[SIndex[0]] - X[SIndex[-1]]) * Y[SIndex[[0, -1]]].mean()
            AArea_tang = AArea_base - np.abs(X[AIndex[0]] - X[AIndex[-1]]) * Y[AIndex[[0, -1]]].mean()
            ICO_base = CArea_base / AArea_base
            ISO_base = SArea_base / AArea_base
            ICO_tang = CArea_tang / AArea_tang
            ISO_tang = SArea_tang / AArea_tang
            # ----------------------------------------------------------------------------------------------------------
            # Recompute the Deconvolution areas/indices, using the stored (already bucketed) Gaussian lists.
            Carbonyl_G  = Binary_to_Array(Data['Deconv_CarbonylList'],  Data['Deconv_CarbonylList_shape'],
                                          Data['Deconv_CarbonylList_dtype'])
            Sulfoxide_G = Binary_to_Array(Data['Deconv_SulfoxideList'], Data['Deconv_SulfoxideList_shape'],
                                          Data['Deconv_SulfoxideList_dtype'])
            Aliphatic_G = Binary_to_Array(Data['Deconv_AliphaticList'], Data['Deconv_AliphaticList_shape'],
                                          Data['Deconv_AliphaticList_dtype'])
            CArea_dec = (Carbonyl_G[:, 2]  * np.sqrt(2 * np.pi) * np.abs(Carbonyl_G[:, 1])).sum()
            SArea_dec = (Sulfoxide_G[:, 2] * np.sqrt(2 * np.pi) * np.abs(Sulfoxide_G[:, 1])).sum()
            AArea_dec = (Aliphatic_G[:, 2] * np.sqrt(2 * np.pi) * np.abs(Aliphatic_G[:, 1])).sum()
            Deconv_ICO = CArea_dec / AArea_dec
            Deconv_ISO = SArea_dec / AArea_dec
            # ----------------------------------------------------------------------------------------------------------
            # Update the record with the freshly recomputed values.
            cursor.execute("""
                UPDATE FTIR SET
                    Carbonyl_Area_Baseline = ?, Sulfoxide_Area_Baseline = ?, Aliphatic_Area_Baseline = ?,
                    Carbonyl_Area_Tangential = ?, Sulfoxide_Area_Tangential = ?, Aliphatic_Area_Tangential = ?,
                    ICO_Baseline = ?, ISO_Baseline = ?, ICO_Tangential = ?, ISO_Tangential = ?,
                    Deconv_ICO = ?, Deconv_ISO = ?
                WHERE id = ?
            """, (CArea_base, SArea_base, AArea_base, CArea_tang, SArea_tang, AArea_tang,
                  ICO_base, ISO_base, ICO_tang, ISO_tang, Deconv_ICO, Deconv_ISO, ID))
            NumUpdated += 1
        except Exception as err:
            NumSkipped += 1
            Errors.append((ID, str(err)))
        if progress_callback:
            progress_callback(i + 1, NumRows)
    # Commit all the changes at once.
    conn.commit()
    # Return the summary of the operation.
    return {'NumRows': NumRows, 'NumUpdated': NumUpdated, 'NumSkipped': NumSkipped, 'Errors': Errors}
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
