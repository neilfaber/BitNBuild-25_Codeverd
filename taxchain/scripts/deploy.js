const hre = require("hardhat");

async function main() {
  const TaxRecord = await hre.ethers.getContractFactory("TaxRecord");

  console.log("Deploying TaxRecord...");
  const taxRecord = await TaxRecord.deploy();  // deploys automatically
  await taxRecord.waitForDeployment();        // waits for mining

  console.log("TaxRecord deployed to:", await taxRecord.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
