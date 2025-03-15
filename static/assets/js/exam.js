$(document).ready(function() {
    var questions = {{ exam_Question|safe }};
    var answers = [];
    var currentQuestionIndex = 0;

    function updateSidebarBlocks() {
      $('.right-canva-inner-sections').each(function() {
        var questionId = $(this).data('question-id');
        if (answers.some(a => a.question_id == questionId)) {
          $(this).addClass('attended');
        } else {
          $(this).removeClass('attended');
        }
      });
    }

    function loadProgress() {
      var savedAnswers = localStorage.getItem('examAnswers');
      var savedQuestionIndex = localStorage.getItem('currentQuestionIndex');

      if (savedAnswers) {
        answers = JSON.parse(savedAnswers);
        answers.forEach(answer => {
          $(`input[name="selected_option_${answer.question_id}"][value="${answer.selected_option}"]`).prop('checked', true);
        });
        updateSidebarBlocks();
      }

      if (savedQuestionIndex) {
        currentQuestionIndex = parseInt(savedQuestionIndex);
        $('.question-container').removeClass('active');
        $('#question-' + questions[currentQuestionIndex].Id).addClass('active');
        highlightCurrentBlock(questions[currentQuestionIndex].Id);

        if (currentQuestionIndex == 0) {
          $('.prev-button').hide();
        } else {
          $('.prev-button').show();
        }

        if (currentQuestionIndex == questions.length - 1) {
          $('.next-button').hide();
          $('.submit-button').show();
        } else {
          $('.next-button').show();
          $('.submit-button').hide();
        }
      }
    }

    function saveProgress() {
      localStorage.setItem('examAnswers', JSON.stringify(answers));
      localStorage.setItem('currentQuestionIndex', currentQuestionIndex);
    }

    function handleQuestions(questions) {
      $('.container-for-sidebar-right').empty();
      questions.forEach((question, index) => {
        $('.container-for-sidebar-right').append(`<div class="right-canva-inner-sections" data-question-id="${question.Id}">${index + 1}</div>`);
      });
      updateSidebarBlocks();

      if (questions.length > 0) {
        $('#question-' + questions[0].Id).addClass('active');
        highlightCurrentBlock(questions[0].Id);
        $('.prev-button').hide();
      }

      $('.next-button, .prev-button').on('click', function() {
        var questionId = $(this).data('question-id');
        currentQuestionIndex = questions.findIndex(q => q.Id == questionId);

        if ($(this).hasClass('next-button')) {
          if (currentQuestionIndex < questions.length - 1) {
            $('#question-' + questionId).removeClass('active');
            $('#question-' + questions[currentQuestionIndex + 1].Id).addClass('active');
            highlightCurrentBlock(questions[currentQuestionIndex + 1].Id);

            $('.prev-button').show();
            if (currentQuestionIndex + 1 == questions.length - 1) {
              $('.next-button').hide();
              $('.submit-button').show();
            }
          }
        } else if ($(this).hasClass('prev-button')) {
          if (currentQuestionIndex > 0) {
            $('#question-' + questionId).removeClass('active');
            $('#question-' + questions[currentQuestionIndex - 1].Id).addClass('active');
            highlightCurrentBlock(questions[currentQuestionIndex - 1].Id);

            $('.next-button').show();
            $('.submit-button').hide();
            if (currentQuestionIndex - 1 == 0) {
              $('.prev-button').hide();
            }
          }
        }
        saveProgress();
      });
    }

    function highlightCurrentBlock(questionId) {
      $('.right-canva-inner-sections').removeClass('active');
      $('.right-canva-inner-sections[data-question-id="' + questionId + '"]').addClass('active');
    }

    function collectAnswers() {
      answers = [];
      questions.forEach(question => {
        var selectedOption = $(`input[name="selected_option_${question.Id}"]:checked`).val();
        if (selectedOption) {
          answers.push({
            question_id: question.Id,
            question_text: question.Question,
            selected_option: selectedOption
          });
        }
      });
      updateSidebarBlocks();
      saveProgress();
    }

    function sendAnswersToBackend(answers) {
      $.ajax({
        type: 'POST',
        url: '{% url "SubmitExam" %}',
        data: JSON.stringify(answers),
        contentType: 'application/json',
        beforeSend: function(xhr, settings) {
          xhr.setRequestHeader('X-CSRFToken', '{{ csrf_token }}');
        },
        success: function(response) {
            window.location.href = '{% url "SelectExam" %}';
        },
        error: function(error) {
          console.error('Error sending data:', error);
        }
      });
    }

    function showPopup() {
      var attendedCount = answers.length;
      var totalCount = questions.length;

      $('#attended-count').text(attendedCount);
      $('#total-count').text(totalCount);

      $('.popup-overlay').show();
      $('.popup').show();
    }

    function hidePopup() {
      $('.popup-overlay').hide();
      $('.popup').hide();
    }

    handleQuestions(questions);
    loadProgress();

    $(document).on('click', '.submit-button', function() {
      collectAnswers();
      showPopup();
    });

    $(document).on('click', '#submit-full-exam', function() {
      collectAnswers();
      showPopup();
    });

    $(document).on('click', '.popup .cancel-button', function() {
      hidePopup();
    });

    $(document).on('click', '.popup .submit-button', function() {
      collectAnswers();
      sendAnswersToBackend(answers);
      hidePopup();
    });

    $(document).on('change', 'input[type=radio]', function() {
      collectAnswers();
    });

    $(document).on('click', '.right-canva-inner-sections', function() {
      var questionId = $(this).data('question-id');
      var questionIndex = questions.findIndex(q => q.Id == questionId);

      $('.question-container.active').removeClass('active');
      $('#question-' + questionId).addClass('active');
      currentQuestionIndex = questionIndex;
      highlightCurrentBlock(questionId);

      if (questionIndex == 0) {
        $('.prev-button').hide();
      } else {
        $('.prev-button').show();
      }

      if (questionIndex == questions.length - 1) {
        $('.next-button').hide();
        $('.submit-button').show();
      } else {
        $('.next-button').show();
        $('.submit-button').hide();
      }
      saveProgress();
    });

    window.addEventListener('beforeunload', saveProgress);
  });