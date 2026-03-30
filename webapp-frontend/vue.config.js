const { defineConfig } = require("@vue/cli-service")

const version = Date.now()

module.exports = defineConfig({
  transpileDependencies: true,
  
  chainWebpack: config => {
    // Add version query parameter to all generated assets
    config.output.filename(`js/[name].[contenthash:8].js?v=${version}`)
    config.output.chunkFilename(`js/[name].[contenthash:8].js?v=${version}`)
    
    // Add version to CSS files
    config.plugin("extract-css").tap(args => {
      args[0].filename = `css/[name].[contenthash:8].css?v=${version}`
      args[0].chunkFilename = `css/[name].[contenthash:8].css?v=${version}`
      return args
    })
  }
})
