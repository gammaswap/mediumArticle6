const EthDater = require('ethereum-block-by-date');
const Web3 = require('web3');
const config = require('./config.json');
const web3 = new Web3(new Web3.providers.HttpProvider(config.provider));
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const fs = require('fs');
const path = config.fileName;

async function getBlocks() {
    const csvWriter = createCsvWriter({
      path: path,
      header: [
        {id: 'date', title: 'Date'},
        {id: 'block', title: 'Block'},
        {id: 'timestamp', title: 'Timestamp'},
      ]
    });

    const dater = new EthDater(
        web3 // Web3 object, required.
    );

    // Getting block by period duration. For example: every first block of Monday's noons of October 2019.
    let blocks = await dater.getEvery(
        config.period, // Period, required. Valid value: years, quarters, months, weeks, days, hours, minutes
        config.startDt, // Start date, required. Any valid moment.js value: string, milliseconds, Date() object, moment() object.
        config.endDt, // End date, required. Any valid moment.js value: string, milliseconds, Date() object, moment() object.
        1, // Duration, optional, integer. By default 1.
        true, // Block after, optional. Search for the nearest block before or after the given date. By default true.
        false // Refresh boundaries, optional. Recheck the latest block before request. By default false.
    );

    csvWriter
      .writeRecords(blocks)
      .then(()=> console.log("The CSV file " + path + " was written successfully"));
}

try {
    if (fs.existsSync(path)) {
        //file exists
        let args = [];
        process.argv.forEach(function (val, index, array) {
            if(val.length > 1 && val.startsWith('-')){
                args.push(val);
            }
        });
        if(args.length > 0 && args[0] == '-o') {
            console.log("Overwrite file " + path);
            getBlocks();
        } else {
            console.log("Abort, file " + path + " exists. If wish to overwrite run 'node printBlocksForDates -o'");
        }
    } else {
        console.log("File " + path + " does not exist. Create file");
        getBlocks();
    }
} catch(err) {
    console.error(err);
}