# R's foreign decoder preserves SAS XPORT zero values. See evidence/decoder_audit.csv.
for (name in c('DEMO_J','GHB_J','BMX_J','DIQ_J')) {
  d <- foreign::read.xport(paste0('data/raw/',name,'.xpt'))
  write.csv(d,paste0('data/processed/',name,'.csv'),row.names=FALSE,na='')
}
