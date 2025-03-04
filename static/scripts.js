$(document).ready(function () {
    $('#uploadForm').on('submit', function (e) {
        e.preventDefault();
        var formData = new FormData(this);
        $.ajax({
            url: '/upload_file',
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function (response) {
                if (response.success) {
                    alert('File uploaded successfully');
                } else {
                    alert('File upload failed: ' + response.error);
                }
            },
            error: function (response) {
                alert('An error occurred while uploading the file.');
            }
        });
    });

    $('#search_button').click(function () {
        var teamNumber = $('#team_number').val().trim();
        if (teamNumber === "") {
            alert('Please enter a team number.');
            return;
        }
        $.post('/get_team_averages', { team_number: teamNumber }, function (data) {
            $('#result').text(data.error ? 'Error: ' + data.error : JSON.stringify(data.averages, null, 2));
        }).fail(function (jqXHR, textStatus) {
            $('#result').text('Error: ' + textStatus);
        });
    });

    $('#get_all_averages').click(function () {
        $.post('/get_all_team_averages', function (data) {
            $('#all_averages_result').text(data.error ? 'Error: ' + data.error : JSON.stringify(data.averages, null, 2));
        }).fail(function (jqXHR, textStatus) {
            $('#all_averages_result').text('Error: ' + textStatus);
        });
    });

    $('#get_team_rankings').click(function () {
        $.get('/get_team_rankings', function (data) {
            if (data.error) {
                $('#rank_result').text('Error: ' + data.error);
            } else {
                var result = '';
                var teamsArray = [];
                for (var team in data.team_rankings) {
                    teamsArray.push({ team: team, points: data.team_rankings[team] });
                }
                teamsArray.sort(function (a, b) {
                    return b.points - a.points;
                });
                var rank = 1;
                teamsArray.forEach(function (team) {
                    result += 'Rank ' + rank + ': Team ' + team.team + ' - ' + team.points + ' points\n';
                    rank++;
                });
                $('#rank_result').text(result);
            }
        }).fail(function (jqXHR, textStatus) {
            $('#rank_result').text('Error: ' + textStatus);
        });
    });

    $('#get_match_data').click(function () {
        var teamNumber = $('#match_team_number').val();
        if (teamNumber) {
            $.ajax({
                url: '/get_match_data',
                type: 'GET',
                data: { team_number: teamNumber },
                success: function (response) {
                    if (response.error) {
                        $('#match_result').text(response.error);
                    } else {
                        var result = '';
                        response.match_data.forEach(function (match) {
                            result += 'Match ' + match.Match + ':\n';
                            for (var key in match) {
                                result += key + ': ' + match[key] + '\n';
                            }
                            result += '\n';
                        });
                        $('#match_result').text(result);
                    }
                },
                error: function () {
                    $('#match_result').text('An error occurred while fetching match data.');
                }
            });
        } else {
            $('#match_result').text('Please enter a team number.');
        }
    });

    $('#get_most_died').click(function () {
        $.get('/get_most_died', function (data) {
            if (data.error) {
                $('#most_died_result').text('Error: ' + data.error);
            } else {
                var result = 'Most Broke:\n';
                data.forEach(function (team) {
                    result += 'Team: ' + team.team + ', Count: ' + team.count + '\n';
                });
                $('#most_died_result').text(result);
            }
        }).fail(function (jqXHR, textStatus) {
            $('#most_died_result').text('Error: ' + textStatus);
        });
    });

    $('#calculate_points').click(function () {
        var teamNumbers = [
            $('#red_team_1').val().trim(),
            $('#red_team_2').val().trim(),
            $('#red_team_3').val().trim(),
            $('#blue_team_1').val().trim(),
            $('#blue_team_2').val().trim(),
            $('#blue_team_3').val().trim()
        ];

        if (teamNumbers.includes("")) {
            alert('Please enter all six team numbers.');
            return;
        }

        $.ajax({
            url: '/calculate_match_points',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ team_numbers: teamNumbers }),
            success: function (response) {
                if (response.error) {
                    $('#match_points_result').text('Error: ' + response.error);
                } else {
                    var result = 'Estimated Match Points:\n\n';
                    var redPoints = 0;
                    var bluePoints = 0;

                    for (var i = 0; i < 3; i++) {
                        var teamNumber = teamNumbers[i];
                        var averages = response.averages[teamNumber];
                        result += 'Red Team ' + teamNumber + ' Averages:\n' + JSON.stringify(averages, null, 2) + '\n\n';
                        redPoints += Object.values(averages).reduce((a, b) => a + b, 0);
                    }

                    for (var i = 3; i < 6; i++) {
                        var teamNumber = teamNumbers[i];
                        var averages = response.averages[teamNumber];
                        result += 'Blue Team ' + teamNumber + ' Averages:\n' + JSON.stringify(averages, null, 2) + '\n\n';
                        bluePoints += Object.values(averages).reduce((a, b) => a + b, 0);
                    }

                    result += 'Total Red Alliance Points: ' + redPoints + '\n';
                    result += 'Total Blue Alliance Points: ' + bluePoints + '\n';

                    $('#match_points_result').text(result);
                }
            },
            error: function () {
                $('#match_points_result').text('An error occurred while calculating match points.');
            }
        });
    });

    // Send a request to delete the file when the window is closed
    $(window).on('beforeunload', function () {
        navigator.sendBeacon('/delete_file');
    });
});