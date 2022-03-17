sudo apt-get install -y locales

pip install -r ../requirements.txt
pip install -e .

echo 'export LC_ALL=C.UTF-8' >> ~/.bashrc
echo 'export LANG=C.UTF-8' >> ~/.bashrc
