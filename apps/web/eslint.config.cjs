module.exports = [
  {
    ignores: ["node_modules/**", "dist/**", "build/**", "coverage/**"],
  },
  {
    files: ["**/*.{js,cjs,mjs,ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
    },
    rules: {},
  },
];
