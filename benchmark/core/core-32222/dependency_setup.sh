sudo apt-get install locales
echo "export LC_ALL=C.UTF-8" >> ~/.bashrc

pip install -r ../requirements.txt
pip install -e .

