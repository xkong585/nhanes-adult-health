# Run from the repository root. Never subset the raw frame to complete cases first.
if (nzchar(Sys.getenv('R_LIBS_USER'))) .libPaths(c(Sys.getenv('R_LIBS_USER'), .libPaths()))
library(survey)
stopifnot(as.character(packageVersion("survey")) == "4.5")
options(survey.lonely.psu='fail')
d <- read.csv('data/processed/merged.csv', stringsAsFactors=FALSE)
for (flag in c('mec_usable','adult','main_model_complete')) d[[flag]] <- d[[flag]] %in% c(TRUE,'True')
d$sex <- factor(d$RIAGENDR, levels=c(1,2), labels=c('Male','Female'))
d$race <- factor(d$RIDRETH3)
d$age_group <- cut(d$RIDAGEYR, breaks=c(20,40,60,Inf), right=FALSE, labels=c('20-39','40-59','60+'))
d$bmi_band <- cut(d$BMXBMI, breaks=c(-Inf,18.5,25,30,35,40,Inf), right=FALSE,
                  labels=c('<18.5','18.5-<25','25-<30','30-<35','35-<40','40+'))
mec <- subset(d, mec_usable)
stopifnot(all(complete.cases(mec[c('SDMVSTRA','SDMVPSU','WTMEC2YR')])))
full <- svydesign(ids=~SDMVPSU, strata=~SDMVSTRA, weights=~WTMEC2YR, nest=TRUE, data=mec)
adult <- subset(full, adult)
a <- subset(adult, main_model_complete)
capture.output({ print(full); cat('\nComplete-case domain design df:',degf(a),'\n'); print(sessionInfo()) }, file='evidence/design_checks.txt')
write.csv(data.frame(design=c('full_MEC','adult_MEC','complete_case'),
                    n=c(nrow(full$variables),nrow(adult$variables),nrow(a$variables)),
                    df=c(degf(full),degf(adult),degf(a))), 'evidence/design_summary.csv',row.names=FALSE)

mean_row <- function(design, variable, group) {
  stat <- svymean(as.formula(paste0('~',variable)),design,na.rm=TRUE)
  estimate <- unname(coef(stat)[1]); se <- unname(SE(stat)[1]); df <- degf(design)
  ci <- estimate + c(-1,1)*qt(.975,df)*se
  data.frame(group=group,variable=variable,n=nrow(design$variables),estimate=estimate,se=se,
             lower=ci[1],upper=ci[2],df=df,unweighted=mean(design$variables[[variable]]))
}
a <- update(a, female=as.numeric(sex=='Female'))
rows <- list()
for(g in c('All adults','20-39','40-59','60+')) {
  domain <- if(g=='All adults') a else subset(a, age_group==g)
  for(v in c('BMXBMI','LBXGH','RIDAGEYR','female')) rows[[length(rows)+1]] <- mean_row(domain,v,g)
}
write.csv(do.call(rbind,rows),'evidence/table1.csv',row.names=FALSE)
bands <- lapply(levels(a$variables$bmi_band),function(b) mean_row(subset(a,bmi_band==b),'LBXGH',b))
write.csv(do.call(rbind,bands),'evidence/bmi_band_means.csv',row.names=FALSE)

fits <- list(
  primary=svyglm(LBXGH~bmi5+RIDAGEYR+sex,design=a),
  no_reported_diabetes=svyglm(LBXGH~bmi5+RIDAGEYR+sex,design=subset(a,DIQ010==2)),
  race_adjusted=svyglm(LBXGH~bmi5+RIDAGEYR+sex+race,design=subset(a,!is.na(race))),
  quadratic=svyglm(LBXGH~bmi5+I(bmi5^2)+RIDAGEYR+sex,design=a)
)
model_table <- function(fit,name) {
  ci <- confint(fit,ddf=fit$df.residual)
  s <- coef(summary(fit))
  data.frame(model=name,term=rownames(s),estimate=s[,1],se=s[,2],lower=ci[,1],upper=ci[,2],
             p_value=s[,4],df=fit$df.residual,n=nobs(fit),row.names=NULL)
}
models <- do.call(rbind,Map(model_table,fits,names(fits)))
write.csv(models,'evidence/model_results.csv',row.names=FALSE)
write.csv(subset(models,term=='bmi5' & model!='quadratic'),'evidence/sensitivity_table.csv',row.names=FALSE)
# Aggregate diagnostics only. Individual residuals and influence values stay local.
a <- update(a,residual=as.numeric(residuals(fits$primary,type='response')))
residuals_by_band <- lapply(levels(a$variables$bmi_band),function(b) mean_row(subset(a,bmi_band==b),'residual',b))
write.csv(do.call(rbind,residuals_by_band),'evidence/residual_band_means.csv',row.names=FALSE)
lev <- hatvalues(fits$primary)
write.csv(data.frame(metric=c('max_leverage','leverage_over_2p_n','weighted_residual_RMSE'),
                     value=c(max(lev),sum(lev>2*length(coef(fits$primary))/nobs(fits$primary)),
                             sqrt(weighted.mean(residuals(fits$primary)^2,weights(a))))),
          'evidence/diagnostics.csv',row.names=FALSE)
writeLines(trimws(readLines('evidence/design_checks.txt'),which='right'),'evidence/design_checks.txt')
# Survey variance cross-check uses full design PSU structure even for domains.
write.csv(data.frame(variable=c('BMXBMI','LBXGH'),se=sapply(c('BMXBMI','LBXGH'),
          function(v) as.numeric(SE(svymean(as.formula(paste0('~',v)),a))))),
          'evidence/r_variance_reference.csv',row.names=FALSE)
