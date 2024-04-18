

module.exports = {
    themeConfig: {
        sidebar:{
            // docs文件夹下面的accumulate文件夹 文档中md文件 书写的位置(命名随意)
            '/accumulate/': [
                '/accumulate/', // accumulate文件夹的README.md 不是下拉框形式
                {
                    title: '侧边栏下拉框的标题1',
                    children: [
                        '/accumulate/JS/test', // 以docs为根目录来查找文件
                        // 上面地址查找的是：docs>accumulate>JS>test.md 文件
                        // 自动加.md 每个子选项的标题 是该md文件中的第一个h1/h2/h3标题
                    ]
                }
            ],
            // docs文件夹下面的algorithm文件夹 这是第二组侧边栏 跟第一组侧边栏没关系
            '/algorithm/': [
                '/algorithm/',
                {
                    title: '第二组侧边栏下拉框的标题1',
                    children: [
                        '/algorithm/simple/test'
                    ]
                }
            ]
        }
    }
}
