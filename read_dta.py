import pyreadstat

df, meta = pyreadstat.read_dta(r"C:\Users\jaber\OneDrive\Desktop\Research_JaberChowdhury\Data\Reference\11112018_1_full.dta")
for col in df.columns:
    print(col)
    