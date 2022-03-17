sudo apt-get install locales
echo "export LC_ALL=C.UTF-8" >> ~/.bashrc
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y # install rust
source $HOME/.cargo/env

pip install -r ../requirements.txt
pip install -e ".[dev]" --no-deps

