# AutoFTIR

[![GitHub License](https://img.shields.io/badge/License-GPL_3.0-yellow.svg)](https://github.com/TFHRC-ABML/AutoFTIR/blob/main/LICENSE)

**[paper](XXXX)**

Authors and Contributors:
- *S. Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)*
- *Behnam Jahangiri (behnam.jahangiri.ctr@dot.gov)*
- *Adrian Anderiescu (adrian.anderiescu.ctr@dot.gov)*
- *Aaron Leavitt (aaron.leavitt@dot.gov)*
- *David Mensching (david.mensching@dot.gov)*


This repository contains the official implementation of the **"AutoFTIR"**.

The **AutoFTIR** is a user-friendly Graphical User Interface (GUI) developed in Python to assist pavement engineers in analyzing the Fourier Transform Infrared (FTIR) spectra of asphalt binders. The tool offers the following key features:

- **Data Preprocessing**: Process raw FTIR spectra by applying baseline correction using the Asymmetric Least Squares (ALS) Smoothing method, followed by normalization of the largest peak to 0.15 within the wavenumber range of 600 to 1800 cm⁻¹.

- **Deconvolution Analysis**: Perform deconvolution analysis by fitting Gaussian functions to distinct peaks in the FTIR spectra and calculating the corresponding carbonyl and sulfoxide indices.

- **Peak Recognition Facilitator**: Provide an intuitive GUI framework to streamline the identification of peaks in the carbonyl, sulfoxide, and aliphatic functional group regions.

- **Database Management**: Store analysis results and preprocessed spectra in an SQLite3 database, enabling organization by binder replicates, binder types, and aging levels.

## Content ##

0. [Setup Instrcution](#setup-instruction)
0. [Sample Dataset](#sample-database)
0. [How to Use](#how-to-use)
0. [Acknowledgement](#acknowledgement)
0. [Citation](#citation)


## Setup Instruction ##

### Requirement:

To run this project, you'll need to have [Conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda or Anaconda) installed in your computer. 

---

### Step 1: Install Conda
Ensure you have Conda installed on your system. You can download and install it from the [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/) website.

**NOTE:** During the installation process, ensure that the Conda path is added to your system environment variables. This step may require administrator rights, and you'll typically have the option to add the path during the installation process. If you miss this step, you can manually add the following three paths to your system's PATH variable.

* `C:\ ...\Anaconda3\`
* `C:\ ...\Anaconda3\Scripts\`
* `C:\ ...\Anaconda3\Library\bin`

---

### Step 2: Clone the Repository

Clone this repository to your local machine:

```bash
git clone https://github.com/TFHRC-ABML/AutoFTIR.git AutoFTIR
cd AutoFTIR
```

---

### Step 3: Setup Python environment

1. Ensure the `environment.yml` file is in the project directory, under `./configs/environment.yml`.

2. Create a new Conda environment using the provided YAML file:

```bash
conda env create --file ./configs/environment.yml
```

3. Activate the environment:

```bash
conda activate ftir
```

---

### Step 4: Run the program 

To run the program, execute the following command:

```bash
python Main_GUI.py
```

## Sample Database ##

As an example, a database containing 329 FTIR test results for 54 different asphalt binders under various aging 
conditions is provided at `./example/PTF5_DB.db`. In this database:

* Each asphalt binder is identified by a ID number (a four-digit identification number).
* The database includes details of the laboratory aging state and number of repetitions.
* A column labeled "IsOutlier" tracks data points that are considered outliers, such as noisy spectra or those that deviate from the trends of other replicates.

The dataset contains both **Original** and **Extracted** asphalt binders. Original asphalt binders were sourced from asphalt plants and producers, while extracted asphalt binders were obtained from various asphalt mixtures, which included varying percentages of RAP content (0%, 20%, and 40% by weight of total mixture). Additionally, the dataset includes SBS-modified and rejuvenated asphalt binders. Users can either create their own database or load the provided example database to start working with the software.

When creating or loading a database, users can add FTIR test results to perform the required analysis. To do so, the FTIR spectrum must be provided as a `*.dpt` file. This file must be a text-based, two-column, comma-delimited format containing:
1. Wavenumbers (in cm⁻¹)
2. Absorbance values of the asphalt binder samples

The file must cover at least the wavenumber range of 550 to 1850 cm⁻¹. Example input `*.dpt` files are included in the project, such as `./example/B7042_FTIR_Rep1_1PAV.dpt`.

## How to Use ##

Upon running the code, the user will be prompted to review and accept the "Terms of Use and Agreement", and upon accepting will be directed to the welcome page (see [Figure 1](#fig-welcome)). Here the user can either create a new database or load an existing one. An example database, `./example/PTF5_DB.pd` database, is provided with the package. 

<a id="fig-welcome"></a>
<p align="center">
  <img src="./assets/WelcomePage.png" alt="Figure 1: Welcome page" width="500">
</p>
<p align="center"><b>Figure 1:</b> Welcome Page</p>

The main page (see [Figure 2](#fig-main-nodata)) appears after loading the database. User can use the "Add more data to DB" button to select more `*.dpt` files to analyze and add them to the database. 

<a id="fig-main-nodata"></a>
<p align="center">
  <img src="./assets/MainPage_NoData.png" alt="Figure 2: Main page (no data loaded)" width="700">
</p>
<p align="center"><b>Figure 2:</b> Main Page (No Data Loaded)</p>


After selecting a `*.dpt` file(s), it is loaded into the main page as shown in [Figure 3](#fig-main-data). The deconvolution analysis method is run by default and the results are available in the group box shown on the right middle section of [Figure 3](#fig-main-data). The peaks for carbonyl, sulfoxide, and aliphatic functional groups are automatically detected and shown as highlighted regions in the corresponding graphs. However, it is noted that this peak recognition algorithm may not be fully reliable, and the user should trim the peak boundaries as needed using the spin boxes in the right group box in the main page. The user can then either accept the analysis results by clicking on "OK" button, mark the analysis results as outlier, or discard the current analysis.

<a id="fig-main-data"></a>
<p align="center">
  <img src="./assets/MainPage_DataImported.png" alt="Figure 3: Main page (data loaded)" width="700">
</p>
<p align="center"><b>Figure 3:</b> Main Page (Data Loaded)</p>


By clicking on "Review and Edit DB", the user will have access to all test results stored in the database (see [Figure 4](#fig-review)). In this page, the user can filter the stored data based on their ID number and laboratory aging level. User can also select each row of the data by clicking on any cell, and then use the "Review/Modify Selected Row" button to review or make changes to the preprocessing and analysis of that specific test data. 

<a id="fig-review"></a>
<p align="center">
  <img src="./assets/ReviewPage.png" alt="Figure 4: Review page" width="700">
</p>
<p align="center"><b>Figure 4:</b> Review Page</p>

From the main page, the user can click on "Analyze DB and Export to Excel" button to combine different replicates and create an Excel export file. In addition, the analysis results are also available by clicking on the "Show Analysis Results" button, as shown in [Figure 5](#fig-analysis). The columns representing the Coefficient of Variation (COV) of each parameter are also colormaps, indicating high COV values, so that the user can perform further quality control checks. 

<a id="fig-analysis"></a>
<p align="center">
  <img src="./assets/AnalysisPage.png" alt="Figure 5: Analysis page" width="700">
</p>
<p align="center"><b>Figure 5:</b> Analysis Page</p>

## Acknowledgement ##

We extend our sincere gratitude to Bethel La Plana and Steve Portillo for their contributions in preparing aged asphalt binder samples and performing FTIR testing; and to Scott Parobeck and Frank Davis for managing asphalt mixtures and extractions.

## Citation ##

If you use our code or method in your work, please cite the following:

```bibtex
@misc{AbdollahiFTIRAnalysisTool2025,
  title = {Development of an Automated FTIR Analysis Framework for Asphalt Binders Using Asymmetric Least Squares Smoothing and Deconvolution},
  author = {Abdollahi, Seyed Farhad and Jahangiri, Behnam, Andriescu, Adrian, Leavitt, Aaron and Mensching, David},
  year = {TBD},
  month = XX,
  publisher = {Road Materials and Pavement Design},
  doi = {XXXXX},
  urldate = {2024-10-09},
  archiveprefix = {XXX},
  langid = {english},
  keywords = {FTIR,asphalt binder,deconvolution,oxidation,aging,RTFO,PAV,pavement testing facility,recycling agents,AutoFTIR}
}
```

Please direct any questions to Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov).