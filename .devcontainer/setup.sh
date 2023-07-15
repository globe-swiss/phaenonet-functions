git checkout master
git submodule update --init --recursive
gh codespace rebuild -c $CODESPACE_NAME
