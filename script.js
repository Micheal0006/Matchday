(function () {
  const $ = id => document.getElementById(id);

  const leagueSelect = $('league');
  const teamHome = $('teamHome');
  const teamAway = $('teamAway');
  const predictBtn = $('predictBtn');

  leagueSelect.addEventListener('change', () => {
    const code = leagueSelect.value;
    resetTeamSelect(teamHome, 'Loading teams…');
    resetTeamSelect(teamAway, 'Loading teams…');
    predictBtn.disabled = true;
    $('result').classList.remove('show');
    showStatus('', false);

    if (!code) {
      resetTeamSelect(teamHome, 'Select league first…');
      resetTeamSelect(teamAway, 'Select league first…');
      return;
    }

    fetch('/api/teams?competition=' + encodeURIComponent(code))
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          showStatus(data.error, true);
          resetTeamSelect(teamHome, 'Failed to load teams');
          resetTeamSelect(teamAway, 'Failed to load teams');
          return;
        }
        populateTeams(teamHome, data.teams);
        populateTeams(teamAway, data.teams);
      })
      .catch(() => showStatus('Could not load teams — check the server is running.', true));
  });

  function resetTeamSelect(select, placeholder) {
    select.innerHTML = '<option value="">' + placeholder + '</option>';
    select.disabled = true;
  }

  function populateTeams(select, teams) {
    select.innerHTML = '<option value="">Select team…</option>';
    teams.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = t.name;
      select.appendChild(opt);
    });
    select.disabled = false;
  }

  function checkReady() {
    predictBtn.disabled = !(teamHome.value && teamAway.value && teamHome.value !== teamAway.value);
    if (teamHome.value && teamAway.value && teamHome.value === teamAway.value) {
      showStatus('Pick two different teams', true);
    } else {
      showStatus('', false);
    }
  }

  teamHome.addEventListener('change', checkReady);
  teamAway.addEventListener('change', checkReady);

  function showStatus(msg, isError) {
    const el = $('status');
    el.textContent = msg;
    el.classList.toggle('error', !!isError);
  }

  function predict() {
    showStatus('Fetching live form and running the model…', false);
    $('result').classList.remove('show');

    const params = new URLSearchParams({
      home_id: teamHome.value,
      away_id: teamAway.value,
      home_name: teamHome.options[teamHome.selectedIndex].textContent,
      away_name: teamAway.options[teamAway.selectedIndex].textContent,
    });

    fetch('/api/predict?' + params.toString())
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          showStatus(data.error, true);
          return;
        }
        showStatus('', false);
        renderResult(data);
      })
      .catch(() => showStatus('Prediction failed — check the server logs.', true));
  }

  function renderResult(data) {
    $('resNameHome').textContent = data.home.name.toUpperCase();
    $('resNameAway').textContent = data.away.name.toUpperCase();
    $('scoreHome').textContent = data.score.home;
    $('scoreAway').textContent = data.score.away;
    $('scoreNote').textContent = 'MOST LIKELY SCORELINE · xG ' + data.lambda_home + ' – ' + data.lambda_away;

    $('probNameHome').textContent = data.home.name + ' win';
    $('probNameAway').textContent = data.away.name + ' win';
    $('barHome').style.width = data.probabilities.home_win + '%';
    $('barDraw').style.width = data.probabilities.draw + '%';
    $('barAway').style.width = data.probabilities.away_win + '%';
    $('pctHome').textContent = data.probabilities.home_win + '%';
    $('pctDraw').textContent = data.probabilities.draw + '%';
    $('pctAway').textContent = data.probabilities.away_win + '%';

    const list = $('breakdownList');
    list.innerHTML = '';
    const rows = [
      [data.home.name + ' — last ' + data.home.games_found + ' games', 'Scored ' + data.home.avg_scored.toFixed(2) + ' / conceded ' + data.home.avg_conceded.toFixed(2) + ' per game'],
      [data.away.name + ' — last ' + data.away.games_found + ' games', 'Scored ' + data.away.avg_scored.toFixed(2) + ' / conceded ' + data.away.avg_conceded.toFixed(2) + ' per game'],
      ['Head-to-head', data.head_to_head.played > 0 ? data.home.name + ' won ' + data.head_to_head.home_wins + ' of last ' + data.head_to_head.played : 'No recent meetings found'],
    ];
    rows.forEach(([name, val]) => {
      const row = document.createElement('div');
      row.className = 'factor';
      row.innerHTML = '<span class="factor-name">' + name + '</span><span class="factor-val">' + val + '</span>';
      list.appendChild(row);
    });

    $('result').classList.add('show');
    $('result').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  predictBtn.addEventListener('click', predict);
})();
