const path = require("path");
const { getDefaultConfig } = require("@expo/metro-config");

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, "../..");

const config = getDefaultConfig(projectRoot);

config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(workspaceRoot, "node_modules"),
  path.resolve(projectRoot, "node_modules")
];
config.resolver.disableHierarchicalLookup = true;
config.resolver.extraNodeModules = {
  "@ai-health/ui": path.resolve(workspaceRoot, "packages/ui"),
  "@ai-health/schemas": path.resolve(workspaceRoot, "packages/schemas"),
  "@ai-health/api-client": path.resolve(workspaceRoot, "packages/api-client")
};

module.exports = config;
