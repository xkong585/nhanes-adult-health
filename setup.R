# Use a project-local package library; refuse unreviewed survey upgrades.
dir.create('.Rlibrary',showWarnings=FALSE)
.libPaths(c(normalizePath('.Rlibrary'),.libPaths()))
if (!requireNamespace('survey',quietly=TRUE)) install.packages('survey',repos='https://cloud.r-project.org')
if (as.character(packageVersion('survey'))!='4.5') stop('Expected survey 4.5; inspect and explicitly update the analysis environment before proceeding')
