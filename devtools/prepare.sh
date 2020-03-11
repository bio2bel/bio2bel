#!/usr/bin/env fish

if vf ls | grep bio2bel
  vf activate bio2bel
else
  vf new bio2bel
end

# install this thing
pip install PyGithub

set DIR (dirname (status --current-filename))
python $DIR/download_repos.py
