rm -rf /root/uitest
git clone -b master http://aigcdeploy:aigcdeploy@git.zalldigital.cn/z-test/uitest.git
cd /root/uitest/mango-console/
npm i
npm run build
