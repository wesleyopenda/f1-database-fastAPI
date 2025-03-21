document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("compare-form").addEventListener("submit", function (event) {
        event.preventDefault();
        compareDrivers();
    });
});

function compareDrivers() {
    let driver1 = document.getElementById("driver1").value;
    let driver2 = document.getElementById("driver2").value;

    fetch("/compare-drivers", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({
            "driver1": driver1,
            "driver2": driver2
        })
    })
    .then(response => response.json())
    .then(data => {
        let tableBody = document.getElementById("comparison-results");
        tableBody.innerHTML = "";

        Object.keys(data.comparison).forEach(stat => {
            let row = document.createElement("tr");

            let statCell = document.createElement("td");
            statCell.textContent = stat;
            row.appendChild(statCell);

            let driver1Cell = document.createElement("td");
            driver1Cell.textContent = data.comparison[stat].driver1;
            driver1Cell.style.backgroundColor = data.comparison[stat].better === "driver1" ? "lightgreen" : "";
            row.appendChild(driver1Cell);

            let driver2Cell = document.createElement("td");
            driver2Cell.textContent = data.comparison[stat].driver2;
            driver2Cell.style.backgroundColor = data.comparison[stat].better === "driver2" ? "lightgreen" : "";
            row.appendChild(driver2Cell);

            tableBody.appendChild(row);
        });
    })
    .catch(error => console.error("Error comparing drivers:", error));
}
