# Title: Creating a new SQL table for storing the FTIR data. 
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/24/2024
# ======================================================================================================================

# Importing the required libraries.
import os
import sqlite3
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
        Wavenumber BOLB,
        Wavenumber_shape TEXT,
        Wavenumber_dtype TEXT, 
        Absorption BOLB,
        Absorption_shape TEXT,
        Absorption_dtype TEXT,
        RawWavenumber BOLB,
        RawWavenumber_shape TEXT,
        RawWavenumber_dtype TEXT,
        RawAbsorbance BOLB,
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
        Deconv_GaussianList BOLB,  
        Deconv_GaussianList_shape TEXT,  
        Deconv_GaussianList_dtype TEXT,
        Deconv_CarbonylList BOLB,  
        Deconv_CarbonylList_shape TEXT,  
        Deconv_CarbonylList_dtype TEXT, 
        Deconv_SulfoxideList BOLB, 
        Deconv_SulfoxideList_shape TEXT, 
        Deconv_SulfoxideList_dtype TEXT, 
        Deconv_AliphaticList BOLB, 
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
    fnameNoExt = os.path.splitext(FileName)[0]

    # get the values through a try/except statement.
    try:
        # Get the B-number. 
        if fnameNoExt[0] != 'B':
            raise Exception('Wrong file name')
        Bnumber = int(fnameNoExt[1:].split('_')[0])
        if Bnumber < 1000: 
            raise Exception('Expecting at least 4-digit number!')
        # Check for file name structure. 
        if 'FTIR_Rep' not in fnameNoExt:
            raise Exception('File name not correct! (FTIR_Rep not in file name)!!!')
        # Get the repetition number. 
        Rep = int(fnameNoExt.split('FTIR_Rep')[1].split('_')[0])
        # Get the aging level.
        Aging = fnameNoExt.split(f'FTIR_Rep{Rep}_')[1].split('.')[0]
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
