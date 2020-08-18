from collections import defaultdict

from django.db.models import Max
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from judge.contest_format.default import DefaultContestFormat
from judge.contest_format.registry import register_contest_format


@register_contest_format('asdan')
class ASDANContestFormat(DefaultContestFormat):
    name = gettext_lazy('ASDAN')
    def update_participation(self, participation):
        from judge.models.contest import ContestParticipation, ContestSubmission

        points = 0
        format_data = {}

        username = participation.user.user.username
        # Format of a team username is \d+[ABC]
        if len(username) > 1 and username[:-1].isnumeric() and username[-1] in 'ABC':
            team = [username[:-1] + letter for letter in 'ABC']
            team_participations = list(ContestParticipation.objects.filter(
                user__user__username__in=team,
                contest=participation.contest,
            ))
        else:
            team_participations = [participation]
        team_size = len(team_participations)


        for team_participation in team_participations:
            for result in team_participation.submissions.values('problem_id').annotate(
                points=Max('points')
            ):
                problem_format_data = format_data.get(str(result['problem_id']), {})
                problem_format_data['points'] = problem_format_data.get('points', 0) + result['points'] / team_size
                format_data[str(result['problem_id'])] = problem_format_data
                points += result['points'] / team_size


        for team_participation in team_participations:
            team_participation.cumtime = 0
            team_participation.score = points
            team_participation.tiebreaker = 0
            team_participation.format_data = format_data
            team_participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            return format_html(
                u'<td class="{state}"><a href="{url}">{points}</a></td>',
                state=(('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                       self.best_solution_state(format_data['points'], contest_problem.points)),
                url=reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                points=floatformat(format_data['points']),
            )
        else:
            return mark_safe('<td></td>')

    def display_participation_result(self, participation):
        return format_html(
            u'<td class="user-points"><a href="{url}">{points}</td>',
            url=reverse('contest_all_user_submissions',
                        args=[self.contest.key, participation.user.user.username]),
            points=floatformat(participation.score),
        )
