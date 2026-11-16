@echo off
cd /d "C:\Users\Sahil Belchada\Desktop\ly project\smart-portfolio-advisor\analytics-engine"
python training\build_meta_dataset.py --diagnostic --start 2018-01-01 --horizon 5 > phase_2c2_build.log 2>&1