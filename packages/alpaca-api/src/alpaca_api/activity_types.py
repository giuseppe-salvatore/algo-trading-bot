"""
Activity type constants for Alpaca API.

These constants represent the different types of account activities
that can be fetched from the Alpaca API.
"""

# Trade-related activities
FILL = "FILL"  # Order fills (both partial and full fills)
OPTRD = "OPTRD"  # Option trade

# Cash transactions
CSD = "CSD"  # Cash deposit (+)
CSW = "CSW"  # Cash withdrawal (-)
ACATC = "ACATC"  # ACATS IN/OUT (Cash)
ACATS = "ACATS"  # ACATS IN/OUT (Securities)

# Dividend activities
DIV = "DIV"  # Dividends
DIVCGL = "DIVCGL"  # Dividend (capital gain long term)
DIVCGS = "DIVCGS"  # Dividend (capital gain short term)
DIVFEE = "DIVFEE"  # Dividend fee
DIVFT = "DIVFT"  # Dividend adjusted (Foreign Tax Withheld)
DIVNRA = "DIVNRA"  # Dividend adjusted (NRA Withheld)
DIVROC = "DIVROC"  # Dividend return of capital
DIVTW = "DIVTW"  # Dividend adjusted (Tefra Withheld)
DIVTXEX = "DIVTXEX"  # Dividend (tax exempt)

# Interest activities
INT = "INT"  # Interest (credit/margin)
INTNRA = "INTNRA"  # Interest adjusted (NRA Withheld)
INTTW = "INTTW"  # Interest adjusted (Tefra Withheld)

# Corporate actions
NC = "NC"  # Name change
SPLIT = "SPLIT"  # Stock split
MA = "MA"  # Merger/Acquisition
REORG = "REORG"  # Reorg CA
SPIN = "SPIN"  # Stock spinoff

# Option activities
OPASN = "OPASN"  # Option assignment
OPCA = "OPCA"  # Option corporate action
OPCSH = "OPCSH"  # Option cash deliverable for non-standard contracts
OPEXC = "OPEXC"  # Option exercise
OPEXP = "OPEXP"  # Option expiration

# Journal entries
JNL = "JNL"  # Journal entry
JNLC = "JNLC"  # Journal entry (cash)
JNLS = "JNLS"  # Journal entry (stock)

# Fees
FEE = "FEE"  # Fee denominated in USD
CFEE = "CFEE"  # Crypto fee
PTC = "PTC"  # Pass Thru Charge
PTR = "PTR"  # Pass Thru Rebate

# Activity type groups (for convenience)
TRANS = [CSD, CSW, ACATC, ACATS]  # Cash transactions
DIVIDENDS = [
    DIV,
    DIVCGL,
    DIVCGS,
    DIVFEE,
    DIVFT,
    DIVNRA,
    DIVROC,
    DIVTW,
    DIVTXEX,
]  # All dividend types
MISC = [
    INT,
    INTNRA,
    INTTW,
    JNL,
    JNLC,
    JNLS,
    MA,
    NC,
    OPASN,
    OPCA,
    OPCSH,
    OPEXC,
    OPEXP,
    OPTRD,
    PTC,
    PTR,
    REORG,
    SPIN,
    SPLIT,
    FEE,
    CFEE,
]  # Miscellaneous or rarely used activity types
