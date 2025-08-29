require("@nomiclabs/hardhat-ethers");
require("dotenv").config();

module.exports = {
  solidity: "0.8.0",
  networks: {
    optimism: {
      url: process.env.OPTIMISM_RPC_URL,
      accounts: [process.env.PRIVATE_KEY]
    }
    ,
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL,
      accounts: [process.env.SEPOLIA_PRIVATE_KEY || process.env.PRIVATE_KEY]
    }
  }
};
