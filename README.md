Some scripts I wrote as a Research Assistant at the University of Alberta in 2023.

Scripts:
1)	creator_data_extractor.py - Script used to extract all data from kickstarter creator pages. Takes a json file with a list of creator ids and stores results in a sqlite database. Uses multiprocessing to speed up extractions.
2)	extra_project_finder.py - Script used to extract all projects from creators who might’ve been missed during the initial extraction using creator ids from the ICPSR 38050 Kickstarter Data Global (2009-2020) dataset. Takes a json file with a list of creator ids and stores the project data in a sqlite database. Uses multiprocessing to speed up extractions.
3)	html_data_extractor.py - Script used to unzip and extract data from nested zips that stored data for kickstarter campaign html files. Uses the main campaign page and updates page for its information (comment files didn’t load comments and community files weren’t used). Stores results in csv files. Uses multiprocessing to speed up extractions.
4)	project_data_extractor.py - Script for extracting kickstarter projects online. Will need to be updated for the current kickstarter website and any anti scraping countermeasures.
