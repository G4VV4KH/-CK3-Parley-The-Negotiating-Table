# MCA 3.1 preserves player ownership and adds the CK3 1.20 arranger guard.
# Dot-source, then call:
#   @(Test-McaSortContract -McaRoot '...\marriage_calc_assistant')
# Empty output means PASS. Every output item is a failure string. No exit,
# writes, external tools, global settings, or repository dependencies.
# This is a structural source gate, not a claim of native GUI runtime coverage.
function Test-McaSortContract {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$McaRoot)

    $faults = [System.Collections.Generic.List[string]]::new()
    function Fail([string]$Message) { [void]$faults.Add("MCA sort: $Message") }
    function Norm([string]$Text) { return ($Text -replace '\s+', '') }
    function Require([bool]$Condition, [string]$Message) { if (-not $Condition) { Fail $Message } }
    function SameSet($Actual, $Expected, [string]$Label) {
        $a = @($Actual | Sort-Object -Unique)
        $b = @($Expected | Sort-Object -Unique)
        if (($a -join '|') -cne ($b -join '|')) {
            Fail "$Label differs: actual=[$($a -join ', ')] expected=[$($b -join ', ')]"
        }
    }

    # Tokenization preserves quoted GUI expressions and ignores only real comments.
    # Nodes retain their exact token spans and parents: ownership cannot be proved
    # by finding a nearby scope:actor string or by accepting a variable prefix.
    function ParseText([string]$Text, [string]$Label) {
        $matches = [regex]::Matches($Text.TrimStart([char]0xFEFF), '"(?:\\.|[^"\\])*"|#[^\r\n]*|>=|<=|!=|\?=|[{}=<>]|[^\s{}=<>#]+')
        $tokens = @($matches | Where-Object { -not $_.Value.StartsWith('#') } | ForEach-Object { $_.Value })
        $state = @{ Index = 0; Tokens = $tokens; Label = $Label }
        function ReadNodes($Parent, [bool]$InBlock) {
            $nodes = [System.Collections.Generic.List[object]]::new()
            while ($state.Index -lt $state.Tokens.Count) {
                if ($state.Tokens[$state.Index] -eq '}') {
                    if (-not $InBlock) { throw "$($state.Label): unexpected closing brace" }
                    $state.Index++
                    return $nodes.ToArray()
                }
                $start = $state.Index
                $key = $state.Tokens[$state.Index++]
                if ($key -eq '{') { throw "$($state.Label): anonymous block after $($state.Tokens[[Math]::Max(0,$start-6)..$start] -join ' ')" }
                $node = [pscustomobject]@{ Key = $key; Op = ''; Value = ''; Children = @(); Parent = $Parent; Canon = '' }
                if ($state.Index -lt $state.Tokens.Count -and $state.Tokens[$state.Index] -in @('=', '?=', '>', '<', '>=', '<=', '!=')) {
                    $node.Op = $state.Tokens[$state.Index++]
                    if ($state.Index -ge $state.Tokens.Count) { throw "$($state.Label): missing value for $key" }
                    if ($state.Tokens[$state.Index] -eq '{') {
                        $state.Index++
                        $node.Children = @(ReadNodes $node $true)
                    } else {
                        $node.Value = $state.Tokens[$state.Index++]
                        if ($key -eq 'blockoverride' -and $state.Index -lt $state.Tokens.Count -and $state.Tokens[$state.Index] -eq '{') {
                            $state.Index++
                            $node.Children = @(ReadNodes $node $true)
                        }
                    }
                } elseif ($key -in @('blockoverride', 'types', 'type')) {
                    $node.Value = $state.Tokens[$state.Index++]
                    if ($key -eq 'type') {
                        if ($state.Tokens[$state.Index++] -ne '=') { throw "$($state.Label): malformed type declaration" }
                        $node.Value += '=' + $state.Tokens[$state.Index++]
                    }
                    if ($state.Tokens[$state.Index++] -ne '{') { throw "$($state.Label): malformed blockoverride" }
                    $node.Children = @(ReadNodes $node $true)
                }
                $node.Canon = Norm ($state.Tokens[$start..($state.Index - 1)] -join '')
                [void]$nodes.Add($node)
            }
            if ($InBlock) { throw "$($state.Label): missing closing brace" }
            return $nodes.ToArray()
        }
        return @(ReadNodes $null $false)
    }
    function AllNodes($Nodes) {
        foreach ($node in $Nodes) { $node; if ($node.Children.Count) { AllNodes $node.Children } }
    }
    function Children($Node, [string]$Key) { return @($Node.Children | Where-Object Key -CEQ $Key) }
    function OneChild($Node, [string]$Key, [string]$Label) {
        $found = @(Children $Node $Key)
        if ($found.Count -ne 1) { throw "$Label must contain exactly one $Key (found $($found.Count))" }
        return $found[0]
    }
    function Property($Node, [string]$Key) {
        $p = @(Children $Node $Key)
        if ($p.Count -ne 1) { return '' }
        return $p[0].Value.Trim('"')
    }
    function Exact($Node, [string]$Expected, [string]$Label) {
        Require ($Node.Canon -ceq (Norm $Expected)) "$Label changed"
    }
    function HasAncestor($Node, $Ancestor) {
        $p = $Node.Parent
        while ($null -ne $p) { if ([object]::ReferenceEquals($p, $Ancestor)) { return $true }; $p = $p.Parent }
        return $false
    }
    function DescendsVia($Node, $Ancestor, [string]$PropertyName, [string]$Value) {
        $p = $Node.Parent
        while ($null -ne $p -and -not [object]::ReferenceEquals($p, $Ancestor)) {
            if ((Norm (Property $p $PropertyName)) -ceq (Norm $Value)) { return $true }
            $p = $p.Parent
        }
        return $false
    }

    try {
        $sgPath = Join-Path $McaRoot 'common\scripted_guis\tnt_ma_sort.txt'
        $capturePath = Join-Path $McaRoot 'common\script_values\tnt_ma_sort_capture.txt'
        $guiPath = Join-Path $McaRoot 'gui\interaction_marriage.gui'
        foreach ($file in @($sgPath, $capturePath, $guiPath)) {
            if (-not [IO.File]::Exists($file)) { throw "required file missing: $file" }
        }
        $sg = @(ParseText ([IO.File]::ReadAllText($sgPath)) $sgPath)
        $capture = @(ParseText ([IO.File]::ReadAllText($capturePath)) $capturePath)
        $gui = @(ParseText ([IO.File]::ReadAllText($guiPath)) $guiPath)
        $sgNames = @('start', 'collect', 'finalize', 'clear', 'context_valid' | ForEach-Object { "tnt_ma_sort_$_" })
        $captureNames = @('p', 'p_alliance', 'r', 'r_alliance' | ForEach-Object { "tnt_ma_sort_${_}_capture_value" })
        SameSet $sg.Key $sgNames 'scripted-GUI definitions'
        SameSet $capture.Key $captureNames 'capture-value definitions'
        Require ($sg.Count -eq 5) 'scripted-GUI definition count must be five without duplicates'
        Require ($capture.Count -eq 4) 'capture definition count must be four without duplicates'
        $definitions = @{}
        foreach ($entry in $sg) { $definitions[$entry.Key] = $entry }
        $vars = @('cursor', 'day', 'direction', 'expected', 'matrilineal', 'output_count', 'partner', 'received', 'secondary_actor', 'secondary_recipient', 'side', 'state' | ForEach-Object { "tnt_ma_sort_$_" })
        $lists = @('candidates', 'indices', 'keys', 'keys_by_index', 'packed', 'seen' | ForEach-Object { "tnt_ma_sort_$_" })
        $writeOps = @('set_variable', 'change_variable', 'remove_variable', 'add_to_variable_list', 'clear_variable_list')
        $temporaryAliases = @('tnt_ma_sort_candidate', 'tnt_gr_p', 'tnt_ma_sort_order_key', 'tnt_ma_sort_item')
        $temporaryValues = @('integer_n', 'score', 'integer_index', 'integer_score', 'key', 'decoded_index', 'decoded_score', 'last_index', 'sequence_index', 'output_index' | ForEach-Object { "tnt_ma_sort_$_" })
        $writtenVars = [System.Collections.Generic.List[string]]::new()
        $writtenLists = [System.Collections.Generic.List[string]]::new()

        function GuardedRemoval($Node, [string]$Name, [bool]$List) {
            $parent = $Node.Parent
            if ($null -eq $parent -or $parent.Key -cne 'if') { return $false }
            $limits = @(Children $parent 'limit')
            $guard = if ($List) { 'has_variable_list' } else { 'has_variable' }
            return ($limits.Count -eq 1 -and $limits[0].Canon -ceq "limit={$guard=$Name}")
        }
        # Only this small, explicit effect language is authorized. Unknown effect
        # blocks are rejected, including any extra scope-changing iterator.
        function CheckEffects($Nodes, [string]$Owner, [string]$RootOwner, [string]$Definition, [bool]$ReadOnly = $false) {
            foreach ($node in $Nodes) {
                if ($node.Key -in $writeOps) {
                    $name = if ($node.Key -in @('remove_variable', 'clear_variable_list')) { $node.Value } else { Property $node 'name' }
                    $isList = $node.Key -in @('add_to_variable_list', 'clear_variable_list')
                    $allowed = if ($isList) { $lists } else { $vars }
                    Require ($name -cin $allowed) "$Definition unauthorized $($node.Key) name '$name'"
                    Require ($Owner -ceq 'player' -and -not $ReadOnly) "$Definition $($node.Key) '$name' writes in $Owner/read-only scope"
                    if ($isList) { [void]$writtenLists.Add($name) } else { [void]$writtenVars.Add($name) }
                    if ($node.Key -in @('remove_variable', 'clear_variable_list')) {
                        Require (GuardedRemoval $node $name $isList) "$Definition unguarded removal '$name'"
                    }
                    foreach ($nested in @(AllNodes $node.Children)) {
                        if ($nested.Key -in $writeOps -or $nested.Key -match '^(set|change|remove)_global_variable$') {
                            Fail "$Definition nested mutation inside $($node.Key) '$name'"
                        }
                    }
                    continue
                }
                switch -CaseSensitive ($node.Key) {
                    { $_ -in @('if', 'else_if', 'else') } { CheckEffects $node.Children $Owner $RootOwner $Definition $ReadOnly }
                    'limit' { CheckReadOnly $node.Children $Definition }
                    'root' { CheckEffects $node.Children $RootOwner $RootOwner $Definition $ReadOnly }
                    'scope:actor' {
                        $next = if ($Definition -ceq 'tnt_ma_sort_collect') { 'player' } else { 'unknown actor' }
                        CheckEffects $node.Children $next $RootOwner $Definition $ReadOnly
                    }
                    'scope:tnt_ma_sort_partner' { CheckEffects $node.Children 'partner' $RootOwner $Definition $ReadOnly }
                    'ordered_in_list' {
                        Require ($Definition -ceq 'tnt_ma_sort_finalize') "$Definition unexpected numeric iterator"
                        CheckEffects $node.Children 'numeric iterator' $RootOwner $Definition $ReadOnly
                    }
                    'save_scope_value_as' {
                        Require ((Property $node 'name') -cin $temporaryValues) "$Definition unauthorized temporary value alias '$(Property $node 'name')'"
                        CheckReadOnly $node.Children $Definition
                    }
                    'order_by' { CheckReadOnly $node.Children $Definition }
                    'save_temporary_scope_as' {
                        Require ($node.Value -cin $temporaryAliases) "$Definition unauthorized temporary character alias '$($node.Value)'"
                        if ($node.Value -ceq 'tnt_gr_p') { Require ($Owner -ceq 'partner') 'P partner alias must be captured from the passed partner' }
                    }
                    { $_ -in @('variable', 'max', 'check_range_bounds') } {
                        Require ($null -ne $node.Parent -and $node.Parent.Key -ceq 'ordered_in_list') "$Definition unexpected effect parameter $($node.Key)"
                    }
                    default { Fail "$Definition unknown effect or scope '$($node.Key)'" }
                }
            }
        }
        function CheckReadOnly($Nodes, [string]$Definition) {
            foreach ($node in @(AllNodes $Nodes)) {
                if ($node.Key -match '^(?:(?:set|change|remove)_.*variable|(?:add_to|remove_from|clear)_.*list|save_scope_as|add_gold|change_liege|trigger_event)$') {
                    Fail "$Definition mutation '$($node.Key)' in a read-only expression"
                }
            }
        }
        $contextInputs = @('arranger', 'n', 'partner', 'secondary_actor', 'secondary_recipient', 'side', 'matrilineal', 'day' | ForEach-Object { "tnt_ma_sort_$_" })
        foreach ($entry in $sg) {
            Require ((Property $entry 'scope') -ceq 'character') "$($entry.Key) must be character-scoped"
            $inputNodes = @(Children $entry 'saved_scopes')
            $expectedInputs = switch -CaseSensitive ($entry.Key) {
                'tnt_ma_sort_collect' { @('actor', 'tnt_ma_sort_index', 'tnt_ma_sort_alliance') + $contextInputs }
                { $_ -in @('tnt_ma_sort_start', 'tnt_ma_sort_context_valid') } { $contextInputs }
                default { @() }
            }
            SameSet @($inputNodes | ForEach-Object { $_.Children.Key }) @($expectedInputs) "$($entry.Key) declared input scopes"
            $effects = @(Children $entry 'effect')
            if ($entry.Key -ceq 'tnt_ma_sort_context_valid') {
                Require ($effects.Count -eq 0) 'context_valid must have no effect'
            } else {
                Require ($effects.Count -eq 1) "$($entry.Key) must have one effect"
                $rootOwner = if ($entry.Key -ceq 'tnt_ma_sort_collect') { 'candidate' } else { 'player' }
                foreach ($effect in $effects) { CheckEffects $effect.Children $rootOwner $rootOwner $entry.Key }
            }
            foreach ($valid in @(Children $entry 'is_valid')) { CheckReadOnly $valid.Children $entry.Key }
        }
        # Also inspect temporary aliases inside expressions. An input/actor/root
        # alias must never be overwritten before the structural owner proof.
        foreach ($alias in @((AllNodes $sg) | Where-Object Key -CEQ 'save_temporary_scope_as')) {
            Require ($alias.Value -cin $temporaryAliases) "unauthorized temporary scope '$($alias.Value)'"
        }
        foreach ($value in @((AllNodes $sg) | Where-Object Key -CEQ 'save_scope_value_as')) {
            Require ((Property $value 'name') -cin $temporaryValues) "unauthorized temporary value '$(Property $value 'name')'"
        }
        $allAliases = @((AllNodes $sg) | Where-Object Key -CEQ 'save_temporary_scope_as')
        foreach ($pair in @(@('tnt_ma_sort_candidate', 1), @('tnt_gr_p', 1), @('tnt_ma_sort_order_key', 3), @('tnt_ma_sort_item', 3))) {
            Require (@($allAliases | Where-Object Value -CEQ $pair[0]).Count -eq $pair[1]) "temporary alias $($pair[0]) count changed (possible rebinding)"
        }
        SameSet $writtenVars $vars 'persistent variable writes'
        SameSet $writtenLists $lists 'persistent list writes'

        # Definition ownership and capture purity also cover other files, so moving
        # or duplicating a private definition cannot quietly evade this helper.
        foreach ($folder in @('common\scripted_guis', 'common\script_values')) {
            $base = Join-Path $McaRoot $folder
            foreach ($file in @(Get-ChildItem -LiteralPath $base -Filter '*.txt' -Recurse -File -ErrorAction Stop)) {
                if ($file.FullName -in @($sgPath, $capturePath)) { continue }
                $other = @(ParseText ([IO.File]::ReadAllText($file.FullName)) $file.Name)
                foreach ($entry in $other) {
                    Require (-not $entry.Key.StartsWith('tnt_ma_sort_')) "private sort definition outside owned files: $($file.Name):$($entry.Key)"
                }
                if ($folder -ceq 'common\script_values') { CheckReadOnly $other $file.Name }
            }
        }
        foreach ($entry in $capture) {
            $side = if ($entry.Key -match '^tnt_ma_sort_p_') { 'p' } else { 'r' }
            $grade = if ($entry.Key -match '_alliance_') { "tnt_ma_grade_${side}_alliance_value" } else { "tnt_ma_grade_${side}_value" }
            Exact $entry "$($entry.Key)={ value=-10000 if={ limit={ tnt_ma_grade_${side}_available_value>0 } value=$grade } round=yes }" "$($entry.Key) availability/sentinel/grade/rounding"
        }

        $clearEffect = OneChild $definitions['tnt_ma_sort_clear'] 'effect' 'clear'
        Require ($clearEffect.Children.Count -eq 18) 'clear must contain exactly six guarded list clears and twelve guarded variable removals'
        $clearAll = @(AllNodes $clearEffect.Children)
        SameSet @($clearAll | Where-Object Key -CEQ 'remove_variable' | ForEach-Object Value) $vars 'full clear variables'
        SameSet @($clearAll | Where-Object Key -CEQ 'clear_variable_list' | ForEach-Object Value) $lists 'full clear lists'
        Require (@($clearAll | Where-Object { $_.Key -cin @('set_variable', 'change_variable', 'add_to_variable_list') }).Count -eq 0) 'clear must not create state'

        $collectEffect = OneChild $definitions['tnt_ma_sort_collect'] 'effect' 'collect'
        Require (($collectEffect.Children.Key -join '|') -ceq 'save_temporary_scope_as|if') 'collect must capture candidate then enter one authorization gate'
        Exact $collectEffect.Children[0] 'save_temporary_scope_as=tnt_ma_sort_candidate' 'collect candidate capture'
        $collectOuter = OneChild $collectEffect 'if' 'collect effect'
        Exact (OneChild $collectOuter 'limit' 'collect outer gate') 'limit={ exists=scope:actor exists=scope:tnt_ma_sort_arranger scope:actor=scope:tnt_ma_sort_arranger scope:actor={is_ai=no has_variable=tnt_ma_sort_state has_variable=tnt_ma_sort_expected has_variable=tnt_ma_sort_received var:tnt_ma_sort_state=1 var:tnt_ma_sort_received<var:tnt_ma_sort_expected} }' 'collect effect authorization/late-callback gate'
        Require (($collectOuter.Children.Key -join '|') -ceq 'limit|save_scope_value_as|if|else_if|scope:actor') 'collect candidate calculation/player-write phase shape'
        $actor = OneChild $collectOuter 'scope:actor' 'collect write phase'
        Require (($actor.Children.Key -join '|') -ceq 'if|if') 'collect must contain only guarded capture and failure cleanup in actor scope'
        $captureGuard = $actor.Children[0]
        Exact (OneChild $captureGuard 'limit' 'collect player guard') 'limit={has_variable=tnt_ma_sort_state has_variable=tnt_ma_sort_expected has_variable=tnt_ma_sort_received var:tnt_ma_sort_state=1 var:tnt_ma_sort_received<var:tnt_ma_sort_expected}' 'collect player late-callback gate'
        Require (($captureGuard.Children.Key -join '|') -ceq 'limit|if|else') 'collect player gate must contain only guarded capture and failure branch'
        $collectChecks = OneChild (OneChild $captureGuard 'if' 'collect capture branch') 'limit' 'collect snapshot checks'
        foreach ($term in @('var:tnt_ma_sort_expected=scope:tnt_ma_sort_n', 'var:tnt_ma_sort_side=scope:tnt_ma_sort_side', 'var:tnt_ma_sort_matrilineal=scope:tnt_ma_sort_matrilineal', 'var:tnt_ma_sort_day=scope:tnt_ma_sort_day', 'scope:tnt_ma_sort_index>=0', 'scope:tnt_ma_sort_index<var:tnt_ma_sort_expected', 'scope:tnt_ma_sort_score>=-10000', 'scope:tnt_ma_sort_score<=10000', 'scope:tnt_ma_sort_candidate={is_alive=yes}')) {
            Require ($collectChecks.Canon.Contains($term)) "collect snapshot check missing: $term"
        }
        Exact (OneChild $actor.Children[1] 'limit' 'collect failure cleanup') 'limit={has_variable=tnt_ma_sort_state var:tnt_ma_sort_state=3}' 'collect failure cleanup gate'

        # The packet must round-trip its score and native index before being saved.
        # Locking these small arithmetic boundaries catches base/rounding changes
        # which otherwise pass a name-only inventory while selecting the wrong row.
        $packetBodies = @{
            integer_index = 'value=scope:tnt_ma_sort_index floor=yes'
            integer_score = 'value=scope:tnt_ma_sort_score round=yes'
            key = 'value=scope:tnt_ma_sort_integer_score add=10000 multiply=10000 add=9999 subtract=scope:tnt_ma_sort_integer_index'
            decoded_index = 'value=scope:tnt_ma_sort_key modulo=10000 multiply=-1 add=9999'
            decoded_score = 'value=scope:tnt_ma_sort_key subtract={value=scope:tnt_ma_sort_key modulo=10000} divide=10000 subtract=10000'
        }
        $collectNodes = @(AllNodes $collectEffect.Children)
        foreach ($name in $packetBodies.Keys) {
            $assignments = @($collectNodes | Where-Object { $_.Key -ceq 'save_scope_value_as' -and (Property $_ 'name') -ceq "tnt_ma_sort_$name" })
            Require ($assignments.Count -eq 1) "packet $name must be assigned exactly once"
            if ($assignments.Count -eq 1) { Exact $assignments[0] "save_scope_value_as={name=tnt_ma_sort_$name value={$($packetBodies[$name])}}" "packet $name arithmetic" }
        }
        foreach ($check in @('scope:tnt_ma_sort_index=scope:tnt_ma_sort_integer_index', 'scope:tnt_ma_sort_decoded_index=scope:tnt_ma_sort_index', 'scope:tnt_ma_sort_decoded_score=scope:tnt_ma_sort_integer_score', 'scope:tnt_ma_sort_index=scope:tnt_ma_sort_sequence_index')) {
            Require (@($collectNodes | Where-Object { $_.Canon -ceq $check -and $_.Parent.Key -ceq 'limit' }).Count -eq 1) "capture missing integer/identity/sequence proof $check"
        }

        $startEffect = OneChild $definitions['tnt_ma_sort_start'] 'effect' 'start'
        $startBranches = @(Children $startEffect 'if' | Where-Object { $_.Canon.Contains('exists=scope:tnt_ma_sort_n') })
        Require ($startBranches.Count -eq 1) 'start must have one input-validation gate'
        if ($startBranches.Count -eq 1) {
            $startCheck = OneChild $startBranches[0] 'limit' 'start input validation'
            foreach ($term in @('exists=scope:tnt_ma_sort_arranger', 'this=scope:tnt_ma_sort_arranger')) {
                Require ($startCheck.Canon.Contains($term)) "start effect arranger check missing: $term"
            }
        }
        $context = OneChild $definitions['tnt_ma_sort_context_valid'] 'is_valid' 'context validator'
        foreach ($term in @('exists=scope:tnt_ma_sort_arranger', 'this=scope:tnt_ma_sort_arranger', 'has_variable=tnt_ma_sort_state', 'OR={var:tnt_ma_sort_state=1var:tnt_ma_sort_state=2}', 'var:tnt_ma_sort_expected=scope:tnt_ma_sort_n', 'var:tnt_ma_sort_side=scope:tnt_ma_sort_side', 'var:tnt_ma_sort_matrilineal=scope:tnt_ma_sort_matrilineal', 'var:tnt_ma_sort_day=scope:tnt_ma_sort_day')) {
            Require ($context.Canon.Contains($term)) "context check missing: $term"
        }
        foreach ($name in @('partner', 'secondary_actor', 'secondary_recipient')) {
            $term = "OR={AND={NOT={exists=scope:tnt_ma_sort_$name}NOT={exists=var:tnt_ma_sort_$name}}AND={exists=scope:tnt_ma_sort_$name exists=var:tnt_ma_sort_$name var:tnt_ma_sort_$name={this=scope:tnt_ma_sort_$name}}}"
            foreach ($check in @($context, $collectChecks)) { Require ($check.Canon.Contains((Norm $term))) "$($check.Parent.Key) missing exact optional $name identity check" }
        }
        $finalEffect = OneChild $definitions['tnt_ma_sort_finalize'] 'effect' 'finalize'
        Require (($finalEffect.Children.Key -join '|') -ceq 'if') 'finalize must perform all writes under its effect-body late-callback gate'
        $finalOuter = OneChild $finalEffect 'if' 'finalize effect'
        Exact (OneChild $finalOuter 'limit' 'finalize gate') 'limit={has_variable=tnt_ma_sort_state has_variable=tnt_ma_sort_expected has_variable=tnt_ma_sort_received var:tnt_ma_sort_state=1}' 'finalize late-callback gate'
        $passes = @((AllNodes $finalEffect.Children) | Where-Object Key -CEQ 'ordered_in_list')
        Require ($passes.Count -eq 3) 'finalize must use three ordered passes'
        Require ((@($passes | ForEach-Object { Property $_ 'variable' }) -join '|') -ceq 'tnt_ma_sort_seen|tnt_ma_sort_packed|tnt_ma_sort_packed') 'finalize validation/score/native-index pass order changed'
        foreach ($pass in $passes) {
            Require ((Property $pass 'max') -ceq 'var:tnt_ma_sort_expected') 'finalize ordered pass must be bounded by expected count'
            [void](OneChild $pass 'root' 'finalize numeric pass write bridge')
        }
        $ready = @((AllNodes $finalEffect.Children) | Where-Object { $_.Key -ceq 'set_variable' -and (Property $_ 'name') -ceq 'tnt_ma_sort_state' -and (Property $_ 'value') -ceq '2' })
        Require ($ready.Count -eq 1) 'finalize must have one ready-state transition'
        if ($ready.Count -eq 1) {
            $readyLimit = OneChild $ready[0].Parent 'limit' 'ready transition'
            foreach ($name in @('indices', 'keys', 'keys_by_index', 'candidates')) {
                Require ($readyLimit.Canon.Contains((Norm "variable_list_size={name=tnt_ma_sort_$name value=var:tnt_ma_sort_expected}"))) "ready transition missing $name completeness proof"
            }
        }

        # GUI calls are exact native contexts. No candidate variables, stamps, or
        # reconstructed click handlers are admitted by this snapshot exception.
        $guiNodes = @(AllNodes $gui)
        function NamedGui([string]$Name) {
            $found = @($guiNodes | Where-Object { (Property $_ 'name') -ceq $Name })
            if ($found.Count -ne 1) { throw "GUI named node '$Name' count=$($found.Count), expected one" }
            return $found[0]
        }
        function GuiPropertyIs($Node, [string]$Key, [string]$Expected, [string]$Label) {
            Require ((Norm (Property $Node $Key)) -ceq (Norm $Expected)) "$Label $Key changed"
        }
        $playerRoot = 'GuiScope.SetRoot(GetPlayer.MakeScope)'
        $candidateRoot = "GuiScope.SetRoot(CharacterListItem.GetCharacter.MakeScope).AddScope('actor',GetPlayer.MakeScope)"
        $contextScopes = ".AddScope('tnt_ma_sort_arranger',CharacterInteractionConfirmationWindow.GetPuppetOrActor.MakeScope).AddScope('tnt_ma_sort_n',MakeScopeValue(IntToFixedPoint(GetDataModelSize(CharacterSelectionList.GetList)))).AddScope('tnt_ma_sort_partner',CharacterInteractionConfirmationWindow.GetRecipient.MakeScope).AddScope('tnt_ma_sort_secondary_actor',MatchmakerInteractionWindow.GetActorToMatch.MakeScope).AddScope('tnt_ma_sort_secondary_recipient',MatchmakerInteractionWindow.GetRecipientToMatch.MakeScope).AddScope('tnt_ma_sort_side',MakeScopeValue(Select_CFixedPoint(MatchmakerInteractionWindow.IsPickingSecondaryActor,'(CFixedPoint)1','(CFixedPoint)2'))).AddScope('tnt_ma_sort_matrilineal',MakeScopeValue(Select_CFixedPoint(MarriageInteractionWindow.GetMarriageInfo.IsMatrilineal,'(CFixedPoint)1','(CFixedPoint)0'))).AddScope('tnt_ma_sort_day',MakeScopeValue(IntToFixedPoint(GetCurrentDate.GetDateAsTotalDays)))"
        $metaScopes = ".AddScope('tnt_ma_sort_index',MakeScopeValue(IntToFixedPoint(PdxGuiWidget.GetIndexInDataModel))).AddScope('tnt_ma_sort_alliance',MakeScopeValue(Select_CFixedPoint(DataModelHasItems(CharacterListItem.GetOtherCharacterItems),'(CFixedPoint)1','(CFixedPoint)0')))"
        $clearCall = "[GetScriptedGui('tnt_ma_sort_clear').Execute($playerRoot.End)]"
        $collectCall = "[GetScriptedGui('tnt_ma_sort_collect').Execute($candidateRoot$contextScopes$metaScopes.End)]"
        $startCall = "[GetScriptedGui('tnt_ma_sort_start').Execute($playerRoot$contextScopes.End)]"
        $finalCall = "[GetScriptedGui('tnt_ma_sort_finalize').Execute($playerRoot.End)]"
        $contextCall = "GetScriptedGui('tnt_ma_sort_context_valid').IsValid($playerRoot$contextScopes.End)"
        $stateValue = "GetPlayer.MakeScope.GetVariable('tnt_ma_sort_state').GetValueWithDefault('(CFixedPoint)0')"
        $active = "GreaterThan_CFixedPoint($stateValue,'(CFixedPoint)0')"
        $collecting = "EqualTo_CFixedPoint($stateValue,'(CFixedPoint)1')"
        $readyState = "EqualTo_CFixedPoint($stateValue,'(CFixedPoint)2')"
        $notBuilding = 'Not(CharacterSelectionList.IsBuildingList)'
        $calls = @($guiNodes | Where-Object { $_.Value -match "GetScriptedGui\('tnt_ma_sort_(?:start|collect|finalize|clear)'\)\.Execute" })
        foreach ($call in $calls) {
            $name = [regex]::Match($call.Value, "GetScriptedGui\('tnt_ma_sort_([^']+)'\)").Groups[1].Value
            $expected = switch ($name) { start { $startCall }; collect { $collectCall }; finalize { $finalCall }; clear { $clearCall } }
            Require ((Norm $call.Value.Trim('"')) -ceq (Norm $expected)) "GUI $name Execute has wrong root/metadata or extra expression"
            Require ($call.Key -cin @('onclick', 'on_start')) "GUI $name Execute must be an explicit callback"
        }
        foreach ($pair in @(@('start', 1), @('collect', 2), @('finalize', 1))) {
            $count = @($calls | Where-Object { $_.Value.Contains("GetScriptedGui('tnt_ma_sort_$($pair[0])')") }).Count
            Require ($count -eq $pair[1]) "GUI $($pair[0]) callback count=$count expected=$($pair[1])"
        }
        $startButton = NamedGui 'tnt_ma_sort_start_button'
        GuiPropertyIs $startButton 'onclick' $startCall 'sort start'
        GuiPropertyIs $startButton 'enabled' "[And(Not($active),And(And(ObjectsEqual(CharacterInteractionConfirmationWindow.GetActor,GetPlayer),ObjectsEqual(CharacterInteractionConfirmationWindow.GetPuppetOrActor,GetPlayer)),And($notBuilding,And(Not(CharacterSelectionList.FiltersShown),And(GreaterThan_int32(GetDataModelSize(CharacterSelectionList.GetList),'(int32)0'),LessThanOrEqualTo_int32(GetDataModelSize(CharacterSelectionList.GetList),'(int32)9999'))))))]" 'sort start safety'
        foreach ($side in @('p', 'r')) {
            $collector = NamedGui "tnt_ma_sort_collector_$side"
            $captureNode = NamedGui "tnt_ma_sort_capture_$side"
            $activeNode = NamedGui "tnt_ma_sort_capture_${side}_active"
            $sideExpression = if ($side -ceq 'p') { 'MatchmakerInteractionWindow.IsPickingSecondaryActor' } else { 'Not(MatchmakerInteractionWindow.IsPickingSecondaryActor)' }
            GuiPropertyIs $collector 'datamodel' '[CharacterSelectionList.GetList]' "$side full native collector"
            Require (HasAncestor $captureNode $collector) "$side capture outside collector"
            Require ($captureNode.Parent.Key -ceq 'item') "$side native index must be on the item widget"
            Require ([object]::ReferenceEquals($activeNode.Parent, $captureNode)) "$side callback must belong to captured native item"
            GuiPropertyIs $activeNode 'trigger_when' "[And(And($collecting,$notBuilding),$sideExpression)]" "$side capture lifecycle"
            GuiPropertyIs $activeNode 'on_start' $collectCall "$side capture callback"
        }
        $invalid = "And($active,Or(CharacterSelectionList.IsBuildingList,Not($contextCall)))"
        $complete = "And($collecting,And($notBuilding,And(EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tnt_ma_sort_received').GetValueWithDefault('(CFixedPoint)0'),GetPlayer.MakeScope.GetVariable('tnt_ma_sort_expected').GetValueWithDefault('(CFixedPoint)0')),$contextCall)))"
        GuiPropertyIs (NamedGui 'tnt_ma_sort_invalidate') 'trigger_when' "[$invalid]" 'context invalidation'
        GuiPropertyIs (NamedGui 'tnt_ma_sort_invalidate') 'on_start' $clearCall 'context invalidation'
        GuiPropertyIs (NamedGui 'tnt_ma_sort_complete') 'trigger_when' "[$complete]" 'complete snapshot'
        GuiPropertyIs (NamedGui 'tnt_ma_sort_complete') 'on_start' $finalCall 'complete snapshot'

        $freshScore = "EqualTo_CFixedPoint(Select_CFixedPoint(MatchmakerInteractionWindow.IsPickingSecondaryActor,$candidateRoot.AddScope('tnt_gr_p',CharacterInteractionConfirmationWindow.GetRecipient.MakeScope).ScriptValue(Select_CString(DataModelHasItems(CharacterListItem.GetOtherCharacterItems),'tnt_ma_sort_p_alliance_capture_value','tnt_ma_sort_p_capture_value')),$candidateRoot.ScriptValue(Select_CString(DataModelHasItems(CharacterListItem.GetOtherCharacterItems),'tnt_ma_sort_r_alliance_capture_value','tnt_ma_sort_r_capture_value'))),Subtract_CFixedPoint(Divide_CFixedPoint(Subtract_CFixedPoint(Scope.GetValue,Modulo_CFixedPoint(Scope.GetValue,'(CFixedPoint)10000')),'(CFixedPoint)10000'),'(CFixedPoint)10000'))"
        $identity = "And(Or(EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tnt_ma_sort_direction').GetValueWithDefault('(CFixedPoint)0'),'(CFixedPoint)1'),EqualTo_CFixedPoint(GetPlayer.MakeScope.GetVariable('tnt_ma_sort_direction').GetValueWithDefault('(CFixedPoint)0'),'(CFixedPoint)-1')),ObjectsEqual(CharacterListItem.GetCharacter,Scope.Char))"
        $grid = NamedGui 'tnt_ma_sorted_characters_grid'
        $scoreGuard = NamedGui 'tnt_ma_sort_row_score_guard'
        $identityGuard = NamedGui 'tnt_ma_sort_row_identity_guard'
        GuiPropertyIs $grid 'visible' "[And($readyState,$notBuilding)]" 'sorted grid'
        GuiPropertyIs $grid 'enabled' "[And($notBuilding,$contextCall)]" 'sorted grid'
        GuiPropertyIs $grid 'datamodel' "[GetPlayer.MakeScope.GetList('tnt_ma_sort_indices')]" 'sorted grid'
        foreach ($property in @('visible', 'enabled')) {
            GuiPropertyIs $scoreGuard $property "[$freshScore]" 'row fresh score guard'
            GuiPropertyIs $identityGuard $property "[$identity]" 'row identity guard'
        }
        Require (HasAncestor $scoreGuard $grid) 'score guard outside sorted grid'
        Require (HasAncestor $identityGuard $scoreGuard) 'identity guard must be inside fresh-score guard'
        Require (DescendsVia $scoreGuard $grid 'datamodel' "[DataModelSubSpan(CharacterSelectionList.GetList,FixedPointToInt(Scope.GetValue),'(int32)1')]") 'sorted row must project its index into the original native list'
        Require (DescendsVia $scoreGuard $grid 'datamodel' "[DataModelSubSpan(GetPlayer.MakeScope.GetList('tnt_ma_sort_keys_by_index'),FixedPointToInt(Scope.GetValue),'(int32)1')]") 'sorted row missing native-index score packet'
        $rendered = @(Children $identityGuard 'tnt_ma_widget_character_list_item')
        Require ($rendered.Count -eq 1) 'identity guard must own one inherited native row'
        if ($rendered.Count -eq 1) { Require (($rendered[0].Children.Key -join '|') -ceq 'size') 'sorted row must retain inherited native callbacks/context' }
        $watchdog = NamedGui 'tnt_ma_sort_watchdog'
        GuiPropertyIs $watchdog 'datamodel' "[GetPlayer.MakeScope.GetList('tnt_ma_sort_indices')]" 'whole-snapshot watchdog'
        foreach ($pair in @(@('score', $freshScore), @('identity', $identity))) {
            $watch = NamedGui "tnt_ma_sort_watch_$($pair[0])_invalid"
            Require (HasAncestor $watch $watchdog) "offscreen $($pair[0]) guard outside full watchdog"
            GuiPropertyIs $watch 'trigger_when' "[And($readyState,Not($($pair[1])))]" "offscreen $($pair[0]) guard"
            GuiPropertyIs $watch 'on_start' $clearCall "offscreen $($pair[0]) cleanup"
        }

        # Clear before native actions, not after they change selection/context.
        $resetActions = @('MatchmakerInteractionWindow.Close', 'MatchmakerInteractionWindow.OnClear', 'MatchmakerInteractionWindow.OnChangeOrRevertActorCharacter', 'MatchmakerInteractionWindow.OnChangeOrRevertRecipientCharacter', 'MarriageInfo.ToggleMatrilineal', 'MarriageInfo.ToggleGrandWeddingPromise')
        foreach ($action in $resetActions) {
            $native = @($guiNodes | Where-Object { $_.Key -ceq 'onclick' -and $_.Value.Trim('"') -ceq "[$action]" })
            Require ($native.Count -gt 0) "native reset path missing: $action"
            foreach ($node in $native) {
                $clicks = @(Children $node.Parent 'onclick')
                Require ($clicks.Count -eq 2 -and (Norm $clicks[0].Value.Trim('"')) -ceq (Norm $clearCall) -and [object]::ReferenceEquals($clicks[1], $node)) "snapshot must clear before $action"
            }
        }
        $window = NamedGui 'marriage_interaction_window'
        foreach ($name in @('_show', '_hide')) {
            $states = @($window.Children | Where-Object { $_.Key -ceq 'state' -and (Property $_ 'name') -ceq $name })
            Require ($states.Count -eq 1) "window $name lifecycle state missing"
            if ($states.Count -eq 1) { GuiPropertyIs $states[0] 'on_start' $clearCall "window $name lifecycle cleanup" }
        }
        $list = NamedGui 'marriage_window_character_list'
        $listHide = @($list.Children | Where-Object { $_.Key -ceq 'state' -and (Property $_ 'name') -ceq '_hide' })
        Require ($listHide.Count -eq 1) 'list hide lifecycle cleanup missing'
        if ($listHide.Count -eq 1) { GuiPropertyIs $listHide[0] 'on_start' $clearCall 'list hide lifecycle cleanup' }
        GuiPropertyIs (NamedGui 'tnt_ma_sort_native_button') 'onclick' $clearCall 'return to native order'
    } catch { Fail $_.Exception.Message }
    return $faults.ToArray()
}
