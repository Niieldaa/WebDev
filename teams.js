async function loadTeams() {
    try {
        const response = await fetch(
            "https://api.openf1.org/v1/championship_teams?session_key=9839"
        );
        const teams = await response.json();
        const container = document.getElementById("teams-container");

        // Correct team colors matching OpenF1 API names
        const teamColors = {
            "Mercedes": "#00D2BE",
            "Red Bull Racing": "#1E41FF",
            "Ferrari": "#DC0000",
            "McLaren": "#FF8700",
            "Alpine": "#00A1E8",
            "Aston Martin": "#006F62",
            "Alfa Romeo": "#900000",
            "Haas F1 Team": "#E6002B",
            "AlphaTauri": "#2B4562",
            "Williams": "#005AFF",
            "Kick Sauber": "#01C00E",
            "Racing Bulls": "#6C98FF"
        };

        teams.forEach(team => {
            const card = document.createElement("div");
            card.className = "team-card";

            // Trim name to avoid whitespace issues
            const teamName = team.team_name.trim();

            // Apply team color; fallback to gray
            let color = teamColors[teamName] ?? "#f9f9f9";
            card.style.background = color;

            // Add border if color is very light (like Haas white)
            if (color.toLowerCase() === "#ffffff") {
                card.style.border = "1px solid #ccc";
            }

            // Adjust text color for readability
            card.style.color = isColorDark(color) ? "#fff" : "#111";

            card.innerHTML = `
                <h3>${teamName}</h3>
                <p>Position: ${team.position_current ?? "N/A"}</p>
                <p>Points: ${team.points_current ?? "N/A"}</p>
            `;

            container.appendChild(card);
        });

    } catch (error) {
        console.error("Error loading teams:", error);
    }
}

// Helper: check if color is dark
function isColorDark(color) {
    if (color.startsWith("#")) {
        const r = parseInt(color.substr(1, 2), 16);
        const g = parseInt(color.substr(3, 2), 16);
        const b = parseInt(color.substr(5, 2), 16);
        const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
        return luminance < 140;
    }
    return false;
}

// Load teams on page load
loadTeams();