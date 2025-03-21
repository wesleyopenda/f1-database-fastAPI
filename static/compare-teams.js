document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("compare-form").addEventListener("submit", function (event) {
        event.preventDefault();
        compareTeams();
    });
});

function compareTeams() {
    let team1 = document.getElementById("team1").value;
    let team2 = document.getElementById("team2").value;

    fetch("/compare-teams", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({
            "team1": team1,
            "team2": team2
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

            let team1Cell = document.createElement("td");
            team1Cell.textContent = data.comparison[stat].team1;
            team1Cell.style.backgroundColor = data.comparison[stat].better === "team1" ? "lightgreen" : "";
            row.appendChild(team1Cell);

            let team2Cell = document.createElement("td");
            team2Cell.textContent = data.comparison[stat].team2;
            team2Cell.style.backgroundColor = data.comparison[stat].better === "team2" ? "lightgreen" : "";
            row.appendChild(team2Cell);

            tableBody.appendChild(row);
        });
    })
    .catch(error => console.error("Error comparing teams:", error));
}
