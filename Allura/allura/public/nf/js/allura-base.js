(function($) {
    // Setup label help text
    $('label[title]').each(function(){
        var $this = $(this);
        $this.append('<a href="#" class="help_icon"><b data-icon="h" class="ico ico-help"></b></a>');
        $this.tooltip({showURL: false});
    });
    // Setup title-pane widgets
    $('.title-pane .title').click(function(e) {
        e.preventDefault();
        $(this).closest('.title-pane')
            .find('> .content').toggle('fast', function() {
                $(this)
                    .closest('.title-pane').toggleClass('closed').end()
                    .toggleClass('hidden');
            });
    });
    if(window.location.hash) {
        $(window.location.hash + '.title-pane').removeClass('closed');
    }

    // Setup editable widgets
    $('div.editable, span.editable, h1.editable')
        .find('.viewer')
        .append('<a class="edit_btn btn"><b data-icon="p" class="ico ico-pencil"></b></a>')
        .end()
        .click(function(e){
            var editable = $(this).closest('.editable');
            var editor = editable.find('.editor');
            var viewer = editable.find('.viewer');
            if(editor.hasClass('overlap')){
                editor.width(viewer.width());
            }
            editable.addClass('editing')
                    .removeClass('viewing');
            // autoresize textareas will be the wrong size the first time due to being hidden, so nudge them
            editor.find('textarea').change();
            e.stopPropagation();
        })
        .find('a').click(function(event){
            if(!$(this).hasClass('edit_btn')){
                event.stopPropagation();
            }
        })
        .end()
        .end()
        .find('.editor')
        .find('input, select, textarea').each(function(i){
            var $this = $(this);
            var editor = $this.closest('.editor');
            $this.attr('original_val', this.value);
            if(!$('a.cancel_btn', editor).length){
                var save_btns = $('<div class="save_holder"><input type="submit" value="Save"/><a href="#" class="cancel_btn">Cancel</a></div>');
                if(editor.hasClass('multiline')){
                    var save_holder = editor.find('.save_holder');
                    if(save_holder.length){
                        save_holder.append(save_btns);
                    }
                    else{
                        editor.append(save_btns);
                    }
                }
                else{
                    editor.append($('<table class="holder_table"><tr/></table>')
                                .append($('<td/>').append($this))
                                .append($('<td class="save_controls"/>').append($(save_btns)))
                    );
                }
            }
        })
        .end()
        .find('.cancel_btn').click(function(e){
            $(this).closest('.editable')
                        .addClass('viewing')
                        .removeClass('editing')
                        .find('input, select, textarea').each(function(){
                            $(this).val($(this).attr('original_val'));
                        });
            return false;
        });
})(jQuery);

$(function(){
    $('.defaultText').
        focus(function(){
            var $this = $(this);
            if ( $this.val() == $this[0].title ){
                $this.removeClass('defaultTextActive').val('');
            }
        }).
        blur(function(){
            var $this = $(this);
            if ( !$this.val() ){
                $this.addClass('defaultTextActive').val($this[0].title);
            }
        }).
        blur();
    $('.selectText').focus(function(){this.select()});
});

function auto_close( o, timeout ){
    var $o = $(o);
    setTimeout(function(){
        $o.fadeOut('slow');
    }, timeout);
    return $o;
}

function add_close_box( o ){
    return $(o).prepend('<a class="btn close-box"><b data-icon="d" class="ico ico-delete"></b></a>');
}

function flash( html, kind, timeout ){
    kind || (kind = 'notice');
    var $message = add_close_box($('<div class="'+kind+'">').append(html).prependTo('#notifications'));
    timeout && auto_close($message, timeout);
    return $message;
}

function attach_form_retry( form ){
    $(form).submit(function(){
        $form = $(this);

        var $message = $('#save-message');
        $message.length || ($message = flash('<p>saving...</p>').attr('id', 'save-message'));
        var $text = $message.find('p');
        setTimeout(function(){
            // After 7 seconds, express our concern.
            $text.text('The server is taking too long to respond.<br/>Retrying in 30 seconds.');
            $message.
                addClass('error').
                removeClass('notice').
                show();
            setTimeout(function(){
                // After 30 seconds total, give up and try again.
                $text.text('retrying...');
                $message.show();
                $form.submit();
            }, 23000)
        }, 7000);
    });
}

$(function(){
    // Setup notifications.
    $('#flash > div').
        prependTo('#notifications').
        each(function(){
            this.className || (this.className = 'notice');
            auto_close(add_close_box(this), 45000);
        });
    $('#notifications a.close-box').live('click', function(){
        $(this).parent().hide();
    });

    // Add notifications for form submission.
    attach_form_retry('form.can-retry');

    // Make life a little better for Chrome users by setting tab-order on inputs.
    // This won't stop Chrome from tabbing over links, but should stop links from
    // coming "in between" fields.
    var i = 0;
    $('input,textarea,select,button').each(function(){
        $(this).attr('tabindex', i++);
    });

    // Provide prompt text for otherwise empty viewers
    var ws = /^\s*$/;
    $('[data-prompt]').each(function(){
        var $this = $(this);
        if ( ws.test($this.text()) ) {
            $this.css('color', 'gray').text($this.attr('data-prompt'))
        }
    });
});
