document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("query-form").addEventListener("submit", function (event) {
        event.preventDefault();
        queryTeams();
    });
});

function queryTeams() {
    let attribute = document.getElementById("attribute").value;
    let comparison = document.getElementById("comparison").value;
    let value = document.getElementById("value").value;

    fetch("/query-teams", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({
            "attribute": attribute,
            "comparison": comparison,
            "value": value
        })
    })
    .then(response => response.json())
    .then(data => {
        let resultsContainer = document.getElementById("results");
        resultsContainer.innerHTML = "";

        if (data.teams.length === 0) {
            resultsContainer.innerHTML = "<li>No teams found</li>";
            return;
        }

        data.teams.forEach(team => {
            let listItem = document.createElement("li");
            listItem.textContent = `Team: ${team["name"]} | Year Founded: ${team["Year Founded"]} | Titles: ${team["Total Constructor Titles"]}`;
            resultsContainer.appendChild(listItem);
        });
    })
    .catch(error => console.error("Error fetching teams:", error));
}
