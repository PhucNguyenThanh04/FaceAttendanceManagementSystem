// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require("eslint-config-expo/flat");

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ["dist/*"],
    rules: {
      // Async screen loaders and the Expo web color-scheme hydration helper
      // intentionally update state from mount effects.
      "react-hooks/set-state-in-effect": "off",
      "import/no-named-as-default-member": "off",
    },
  }
]);
