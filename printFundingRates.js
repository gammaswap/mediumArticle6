const bitmexFundingRates = require('./bitmexFundingRate.json');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const fs = require('fs');
const path = 'fundingRates.csv';


async function writeFundingRate() {
    const csvWriter = createCsvWriter({
      path: path,
      header: [
        {id: 'timestamp', title: 'Datetime'},
        {id: 'symbol', title: 'Symbol'},
        {id: 'fundingInterval', title: 'FundingInterval'},
        {id: 'fundingRate', title: 'FundingRate'},
        {id: 'fundingRateDaily', title: 'FundingRateDaily'},
      ]
    });

    let rates = [];
    let first = true;
    let i = 0;
    let timestamp = "";
    let symbol = "";
    let fundingRate = 0;
    bitmexFundingRates.forEach((obj) =>{
        if(++i % 3 == 0) {
            rates.push({ timestamp: timestamp, symbol: symbol, fundingRate: fundingRate })
            timestamp = "";
            symbol = "";
            fundingRate = 0;
        }
        if(timestamp == "") {
            timestamp = obj.timestamp;
            symbol = obj.symbol;
        }
        fundingRate += Math.log(obj.fundingRate + 1);
    });
	
	csvWriter
	  .writeRecords(rates)
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
            writeFundingRate();
        } else {
            console.log("Abort, file " + path + " exists. If wish to overwrite run 'node printFundingRates -o'");
        }
    } else {
        console.log("File " + path + " does not exist. Create file");
        writeFundingRate();
    }
} catch(err) {
    console.error(err);
}