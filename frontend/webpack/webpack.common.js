const Path = require("path");
const { CleanWebpackPlugin } = require("clean-webpack-plugin");
// const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
  entry: {
    app: Path.resolve(__dirname, "../src/index.tsx"),
  },
  output: {
    path: Path.join(__dirname, "../build"),
    filename: "js/[name].js",
  },
  optimization: {
    splitChunks: {
      chunks: "all",
      name: "vendors",
    },
  },
  plugins: [
    new CleanWebpackPlugin(),
    // new CopyWebpackPlugin({
    //     patterns: [{from: Path.resolve(__dirname, '../public'), to: 'public'}],
    // }),
    // new HtmlWebpackPlugin({
    //     template: Path.resolve(__dirname, '../src/index.html'),
    // }),
  ],
  // resolve: {
  //     alias: {
  //         '~': Path.resolve(__dirname, '../src'),
  //     },
  // },
  resolve: {
    extensions: [".js", ".jsx", ".ts", ".tsx"],
  },

  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: "ts-loader",
        exclude: /node_modules/,
      },
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
        },
      },
    ],
  },
};
