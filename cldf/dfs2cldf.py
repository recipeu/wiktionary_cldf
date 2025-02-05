"""convert many csv-files to cldf and validate"""

import ast
import json
import logging
import os
import requests
import subprocess
import sys

import pandas as pd

logging.basicConfig(filename='cldf.log', format='%(message)s %(asctime)s',
                    encoding='utf-8', level=logging.WARNING)

REPO = "https://raw.githubusercontent.com/martino-vic/en_borrowings"
LOCALREPO = os.path.dirname(os.getcwd())


class Csv2cldf:
    """Convert one csv file to cldf"""

    def __init__(self, folder: "'raw1' or 'raw2'", lang: str) -> None:
        """initiate variables that are used by the class methods"""

        glotto = "https://raw.githubusercontent.com/glottolog/glottolog-cldf"
        self.dfglotto = pd.read_csv(f"{glotto}/master/cldf/languages.csv")
        self.dfe = self.dfglotto[self.dfglotto["Name"] == "English"]\
            .assign(Language_ID=0)
        self.lg = lang
        self.rpblob = "https://github.com/martino-vic/en_borrowings/blob"
        self.path = f"{LOCALREPO}/{folder}/{self.lg}.csv"
        self.meta = os.path.join(os.getcwd(), self.lg, "metadata.json")

    def main(self) -> None:
        """
        create and write forms.csv, borrowings.csv, \
        languages.csv, metadata.json, readme.md and validate.
        """

        self.metadata(self.forms(), self.borrowings())
        self.lgs()
        self.readme()

    def readme(self) -> None:
        """
        Validate metadata.json. If validation passes write readme.md, \
        else write error message to logfile cldf.log
        """

        rdm = os.path.join(os.getcwd(), self.lg, "readme.md")
        try:  # check pycldf's documentation. write readme if validation passes
            subprocess.run(f"cldf validate {self.meta}").check_returncode()
            with open(rdm, 'w') as f:  # convert to readme
                badge = "[![CLDF validation]"
                badge += f"({REPO}/master/cldf/badge.svg)]"
                badge += f"({self.rpblob}/master/cldf/dfs2cldf.py#L53)\n\n"
                f.write(badge + subprocess.run(f"cldf markdown {self.meta}",
                        capture_output=True, text=True).stdout)
                        
        except subprocess.CalledProcessError:  # else write error to logfile
            logging.warning(subprocess.run(f"cldf validate {self.meta}",
                            capture_output=True, text=True).stdout)

    def lgs(self) -> None:
        """generate and write languages.csv"""

        dfelocal = self.dfe
        dflg = self.dfglotto[self.dfglotto["Name"] == self.lg]
        if dflg.empty:
            dfelocal = dfelocal.append(
                pd.DataFrame([["", self.lg.capitalize()] +
                              [""]*(len(self.dfe.columns)-3) + [1]],
                             columns=self.dfe.columns))
        else:
            dfelocal = dfelocal.append(dflg.assign(Language_ID=1))

        languages = os.path.join(os.getcwd(), self.lg, "languages.csv")
        dfelocal.to_csv(languages, encoding="utf-8", index=False)

    def metadata(self, lenform: int, lenborr: int) -> None:
        """write metadata.json by inserting missing data into template"""

        with open("metadata_template.json") as json_data:
            data = json.load(json_data)

        data['dc:title'] = data['dc:title'] + self.lg.capitalize()
        data['rdf:ID'] = data['rdf:ID'] + self.lg
        data['tables'][0]['dc:extent'] = lenform
        data['tables'][2]['dc:extent'] = lenborr

        with open(self.meta, "w") as j:
            json.dump(data, j)

    def forms(self) -> int:
        """Generate and write forms.csv"""
        dfm = pd.read_csv(self.path).rename(
            columns={"L2_orth": "Form", "L2_ipa": "IPA", "L2_gloss": "Gloss"})
        dfm["_1"] = ["" if isinstance(i, str) else i for i in dfm["L2_etym"]]
        dfm["_2"] = dfm["_1"]  # two dummy cols for the loop

        dfforms = pd.DataFrame()  # this will be the output
        for form, donor in zip(["Form", "IPA", "Gloss"],
                               ["L2_etym", "_1", "_2"]):
            dfforms[form] = list(dfm[form]) + [i for i in dfm[donor]
                                               if isinstance(i, str)]
        dfforms["Language_ID"] = ["0"]*len(list(dfm[donor]))\
            + ["1" for i in dfm[donor] if isinstance(i, str)]
        dfforms.insert(0, "ID", dfforms.index)

        fms = os.path.join(os.getcwd(), self.lg, "forms.csv")
        dfforms.to_csv(fms, encoding="utf-8", index=False)

        return len(dfforms)

    def borrowings(self) -> int:
        """Generate and write borrowings.csv"""

        dfm = pd.read_csv(self.path)
        dfm["ID"] = dfm.index

        dfborr = pd.DataFrame()
        dfborr["Target_Form_ID"] = [i for i, j in zip(dfm.ID, dfm.L2_etym)
                                    if isinstance(j, str)]
        dfborr["Source_Form_ID"] = [i for i in range(len(dfm),
                                                     len(dfm)+len(dfborr))]
        dfborr.insert(0, "ID", dfborr.index)

        brr = os.path.join(os.getcwd(), self.lg, "borrowings.csv")
        dfborr.to_csv(brr, encoding="utf-8", index=False)

        return len(dfborr)


def loop():
    """Apply C2v2cldf().main() to every file in raw1 and raw2"""

    for folder in ["raw2", "raw1"]:
        for file in os.listdir(os.path.join(LOCALREPO, folder)):
            language = file[:-4]
            sys.stdout.write(f"{language}\n")
            try:
                os.mkdir(language)
            except FileExistsError:
                sys.stdout.write(f"folder {language} already exists\n")
                continue

            Csv2cldf(folder, language).main()


if __name__ == "__main__":
        loop()
