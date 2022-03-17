sudo apt-get install -y mysql-server libmysqlclient-dev
sudo apt-get install -y libxml2
sudo apt-get install -y libpq-dev
export SLUGIFY_USES_TEXT_UNIDECODE=yes

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

pip install -r requirements.txt
pip install -e ".[devel]"

export PYTHONIOENCODING=utf-8
