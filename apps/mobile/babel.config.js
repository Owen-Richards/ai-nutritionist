module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: [
      ["expo-router/babel", { lazy: true }],
      [
        "module-resolver",
        {
          extensions: [".ts", ".tsx", ".js", ".json"],
          alias: {
            "@": "./src"
          }
        }
      ]
    ]
  };
};
