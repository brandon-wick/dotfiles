#!/bin/bash

git clone --bare https://github.com/brandon-wick/dotfiles.git $HOME/.cfg
function config {
   /usr/bin/git --git-dir=$HOME/.cfg/ --work-tree=$HOME $@
}
mkdir -p .config-backup
config checkout
if [ $? = 0 ]; then
  echo "Checked out config.";
  else
    echo "Backing up pre-existing dot files.";
    config checkout 2>&1 | egrep "\s+\." | awk {'print $1'} | xargs -I{} mv {} .config-backup/{}
fi;
config checkout
config config status.showUntrackedFiles no

# OS-dependent operations
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        export DISTRO=$(sed -n 's/.*NAME="\(.*\)".*/\1/p' /etc/os-release | head -1)
        if [[ "$DISTRO" == "Ubuntu"* ]]; then
                source $HOME/.distro-dependent-configs/Ubuntu
        elif [[ "$DISTRO" == "CentOS"* ]]; then
                source $HOME/.distro-dependent-configs/CentOS
        fi
        echo "successfully installed configs for ${DISTRO}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
        source $HOME/.distro-dependent-configs/MacOSX
        echo "successfully installed configs for ${OSTYPE}"
else
        echo "platform unknown"
fi


# installing oh-my-zsh and plugins
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting

# install powerline fonts
git clone https://github.com/powerline/fonts.git --depth=1
cd fonts
./install.sh
cd ..
rm -rf fonts

# copy over .zshrc
cat $HOME/.zshrc.pre-oh-my-zsh > $HOME/.zshrc
rm $HOME/.zshrc.pre-oh-my-zsh

# Create venvs for custom commands
cd $HOME/.custom_commands/build_installer
python3 -m venv ./build_installer.env
source build_installer.env/bin/activate
pip install -r requirements.txt
deactivate

cd $HOME/.custom_commands/download_tester
python3 -m venv ./download_tester.env
source download_tester.env/bin/activate
pip install -r requirements.txt
deactivate

cd $HOME/.custom_commands/get_release
python3 -m venv ./get_release.env
source get_release.env/bin/activate
pip install -r requirements.txt
deactivate
chsh -s /bin/zsh
#==============
# And we are done
#==============
echo -e "\n====== All Done!! ======\n"
