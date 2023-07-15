git checkout master
git submodule update --init --recursive
(cd .devcontainer; git checkout master)
(cd .maintenance; git checkout main)
gh codespace rebuild -c $CODESPACE_NAME
