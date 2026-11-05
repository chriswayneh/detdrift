Output demo.gif
Set FontSize 15
Set Width 1100
Set Height 640
Set Theme "Catppuccin Mocha"
Set FontFamily "JetBrains Mono"
Set TypingSpeed 22ms
Set Framerate 24
Set Padding 18
Set WindowBar Colorful
Set Shell bash
Hide
Type `export PATH="$DETDRIFT_BIN_DIR:$PATH"`
Enter
Type `cd "$DETDRIFT_DEMO_HOME"`
Enter
Type `export PS1='demo$ '`
Enter
Type `rm -rf detdrift-demo && mkdir -p detdrift-demo && cd detdrift-demo`
Enter
Type `clear`
Enter
Show

Type `detdrift --version`
Enter
Sleep 0.8s

Type `detdrift init .`
Enter
Sleep 1.4s

Type `detdrift diff --before fixtures/before --after fixtures/before --rules rules`
Enter
Sleep 2.2s

Type `detdrift diff --before fixtures/before --after fixtures/after --rules rules`
Enter
Sleep 3.5s

Sleep 1.2s
