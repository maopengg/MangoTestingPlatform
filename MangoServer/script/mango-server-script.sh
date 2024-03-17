rm -rf /root/uitest
git clone -b master http://aigcdeploy:aigcdeploy@git.zalldigital.cn/z-test/uitest.git

cd /root/uitest/MangoServer
virtualenv venv
source venv/bin/activate
pip install -r /root/uitest/MangoServer/requirements.txt
deactivate
python /root/uitest/MangoServer/manage.py runserver 0.0.0.0:8001

cd /root/uitest/mango-console/
npm i
npm run build
