const hre = require("hardhat");

async function main() {
  const EnhancedBlockDocument = await hre.ethers.getContractFactory("EnhancedBlockDocument");
  const contract = await EnhancedBlockDocument.deploy();
  await contract.deployed();
  console.log("EnhancedBlockDocument deployed to:", contract.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
