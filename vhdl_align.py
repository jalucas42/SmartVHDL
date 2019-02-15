import sublime, sublime_plugin
import re, string, os, imp, sys, pprint

try:
    from .util import vhdl_util
    from .util import sublime_util
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "util"))
    import sublime_util
    import vhdl_util

def plugin_loaded():
    imp.reload(sublime_util)
    imp.reload(vhdl_util)

############################################################################

class VhdlAlign(sublime_plugin.TextCommand):
    pp        = pprint.PrettyPrinter(indent=4)
    s_id_list = r'\w+(?:\s*,[\s\w,]+)?'
    s_comment = r'^(?P<space>[\ \t]*)--[\ \t]*(?P<comment>.*?)(\n|$)'

    def run(self,edit, cmd=""):
        if len(self.view.sel())==0 : return
        upper_case_keywords = self.view.settings().get('vhdl.upper_case_keywords', False)
        tab_size = int(self.view.settings().get('tab_size', 4))
        use_space = self.view.settings().get('translate_tabs_to_spaces')
        self.indent_space = ' '*tab_size
        self.cfg = {
            'tab_size'                      : tab_size, 
            'use_space'                     : use_space, 
            "upper_case_keywords"           : self.view.settings().get("vhdl.upper_case_keywords"       , False),
            "upper_case_ieee"               : self.view.settings().get("vhdl.upper_case_ieee"           , False),
            "upper_case_attributes"         : self.view.settings().get("vhdl.upper_case_attributes"     , False),
            "align_decl.min_qual_len"       : self.view.settings().get("vhdl.align_decl.min_qual_len"   , 0),
            "align_decl.min_name_len"       : self.view.settings().get("vhdl.align_decl.min_name_len"   , 0),
            "align_decl.min_type_len"       : self.view.settings().get("vhdl.align_decl.min_type_len"   , 0),
            "align_decl.min_range_len"      : self.view.settings().get("vhdl.align_decl.min_range_len"  , 0),
            "align_decl.min_init_len"       : self.view.settings().get("vhdl.align_decl.min_init_len"   , 0),
            "align_inst.min_port_len"       : self.view.settings().get("vhdl.align_inst.min_port_len"   , 0),
            "align_inst.min_bind_len"       : self.view.settings().get("vhdl.align_inst.min_bind_len"   , 0),
            "align_entity.min_name_len"     : self.view.settings().get("vhdl.align_entity.min_name_len" , 0),
            "align_entity.min_type_len"     : self.view.settings().get("vhdl.align_entity.min_type_len" , 0),
            "align_entity.min_range_len"    : self.view.settings().get("vhdl.align_entity.min_range_len", 0),
            "align_entity.min_init_len"     : self.view.settings().get("vhdl.align_entity.min_init_len" , 0),
            "align_decl.max_qual_len"       : self.view.settings().get("vhdl.align_decl.max_qual_len"   , 40),
            "align_decl.max_name_len"       : self.view.settings().get("vhdl.align_decl.max_name_len"   , 40),
            "align_decl.max_type_len"       : self.view.settings().get("vhdl.align_decl.max_type_len"   , 40),
            "align_decl.max_range_len"      : self.view.settings().get("vhdl.align_decl.max_range_len"  , 40),
            "align_decl.max_init_len"       : self.view.settings().get("vhdl.align_decl.max_init_len"   , 40),
            "align_inst.max_port_len"       : self.view.settings().get("vhdl.align_inst.max_port_len"   , 40),
            "align_inst.max_bind_len"       : self.view.settings().get("vhdl.align_inst.max_bind_len"   , 40),
            "align_entity.max_name_len"     : self.view.settings().get("vhdl.align_entity.max_name_len" , 40),
            "align_entity.max_type_len"     : self.view.settings().get("vhdl.align_entity.max_type_len" , 40),
            "align_entity.max_range_len"    : self.view.settings().get("vhdl.align_entity.max_range_len", 40),
            "align_entity.max_init_len"     : self.view.settings().get("vhdl.align_entity.max_init_len" , 40),
        }
        # Save information of selected text
        region = self.view.sel()[0]
        row,col = self.view.rowcol(region.a)
        # Extract scope and make sure we have same at beginning and end of the region
        scope = self.view.scope_name(region.a)
        if region.b > region.a :
            if self.view.scope_name(region.b) != scope :
                scope = ''
        txt = ''
        # Component/Entity instantiation
        if '_instantiation' in scope:
            if 'meta.block.entity_instantiation' in scope:
                region = sublime_util.expand_to_scope(self.view,'meta.block.entity_instantiation',region)
            else :
                region = sublime_util.expand_to_scope(self.view,'meta.block.component_instantiation',region)
            # Make sure to get complete line to be able to get initial indentation
            region = self.view.line(region)
            txt  = self.view.substr(region)
            ilvl = self.getIndentLevel(self.view.substr(region))
            txt  = self.alignInstance(txt,ilvl)
        elif 'meta.block.entity.vhdl' in scope or 'meta.block.component.vhdl' in scope:
            if 'meta.block.entity.vhdl' in scope :
                region = sublime_util.expand_to_scope(self.view,'meta.block.entity',region)
            else :
                region = sublime_util.expand_to_scope(self.view,'meta.block.component',region)
            # Make sure to get complete line to be able to get initial indentation
            region = self.view.line(region)
            txt  = self.view.substr(region)
            ilvl = self.getIndentLevel(self.view.substr(region))
            txt  = self.alignEntity(txt,ilvl)
        elif 'meta.block.record.vhdl' in scope:
            region = sublime_util.expand_to_scope(self.view,'meta.block.record',region)
            region = self.view.line(region)
            txt  = self.view.substr(region)
            ilvl = self.getIndentLevel(self.view.substr(region))
            txt  = self.alignRecord(txt,ilvl)
        else :
            t = ''
            for d in ['signal','variable','constant']:
                if 'meta.block.{}'.format(d) in scope:
                    t = d
                    break
            if t:
                region = self.view.line(region)
                # expand selection forward to find all lines with same scope
                # print('[VHDL:Align] Initial region {}'.format(region))
                while 1:
                    p = self.view.find_by_class(region.b,True,sublime.CLASS_WORD_START|sublime.CLASS_PUNCTUATION_START|sublime.CLASS_EMPTY_LINE)
                    scope = self.view.scope_name(p)
                    # print('[VHDL:Align] Forward: Pos={} Scope={} Region={}'.format(p,scope,region))
                    if p<= region.b or 'meta.block.{}'.format(t) not in scope:
                        break
                    region.b = p
                    region = self.view.line(region)
                # expand selection backward to find all lines with same scope
                scope = 'meta.block.{}'.format(t)
                while 1:
                    p = self.view.find_by_class(region.a,False,sublime.CLASS_LINE_START|sublime.CLASS_EMPTY_LINE)
                    p = self.view.find_by_class(p,True,sublime.CLASS_WORD_START|sublime.CLASS_PUNCTUATION_START)
                    scope = self.view.scope_name(p)
                    # print('[VHDL:Align] Backward Pos={} Scope={}'.format(p,scope))
                    if p==-1 or p>= region.a or 'meta.block.{}'.format(t) not in scope:
                        break
                    region.a = p
                    region = self.view.line(region)
                txt  = self.view.substr(region)
                # print('[VHDL:Align] Final region {}:\n{}'.format(region,txt))
                ilvl = self.getIndentLevel(self.view.substr(region))
                txt  = self.alignDecl(txt,ilvl)

        #
        if txt:
            txt = self.setKeywordCase(txt)
            self.view.replace(edit,region,txt)
            sublime_util.move_cursor(self.view,self.view.text_point(row,col))
        else :
            sublime.status_message('No alignment support for this block of code.')
            # We can still capitalize keywords even if we can't align it!
            region = self.view.line(region)
            self.view.replace(edit, region, self.setKeywordCase(self.view.substr(region)))


    def getIndentLevel(self,txt):
        line = txt[:txt.find('\n')]
        # Make sure there is no mix tab/space
        if self.cfg['use_space']:
            line = line.replace('\t',self.indent_space)
        else:
            line = line.replace(self.indent_space,'\t')
        cnt = len(line) - len(line.lstrip())
        if self.cfg['use_space']:
            cnt = int(cnt/self.cfg['tab_size'])
        return cnt

    def alignEntity(self,txt,ilvl):
        # TODO: Extract comment location to be sure to handle all case of strange comment location
        m = re.search(r"""(?six)
            (?P<type>entity|component)\s+(?P<name>\w+)\s+(?:is)?\s+
            (generic\s*\((?P<generic>.*?)\)\s*;\s*)?
            (port\s*\((?P<port>.*?)\)\s*;)\s*
            (?P<ending>end\b(\s+(?P=type))?(\s+(?P=name))?)\s*;
            """, txt, re.MULTILINE)
        if m is None:
            return txt

        txt_new = '\t'*(ilvl)
        txt_new += '{} {} is \n'.format(m.group('type'),m.group('name'))

        if m.group('generic') :
            # Extract all params info to know width of each for future alignement
            params = vhdl_util.clean_comment(m.group('generic'))
            re_params = r'''(?six)^[\ \t]*
                (?P<name>\w+)[\ \t]*:[\ \t]*
                (?P<type>\w+)\b[\ \t]*
                (?P<range>\(.+?\))?
                (?:[\ \t]*:=[\ \t]*(?P<init>.*?))?
                [\ \t]*(?P<end>;)?[\ \t]*(?:--[\ \t]*(?P<comment>[^\n]*))?$'''

            decl = re.findall(re_params, params ,flags=re.MULTILINE)
            name_len_l  = [] if not decl else [len(x[0].strip()) for x in decl]
            type_len_l  = [] if not decl else [len(x[1].strip()) for x in decl]
            range_len_l = [] if not decl else [len(x[2].strip()) for x in decl]
            init_len_l  = [] if not decl else [len(x[3].strip()) for x in decl]
            name_len  = 0 if not name_len_l  else max(name_len_l )
            type_len  = 0 if not type_len_l  else max(type_len_l )
            range_len = 0 if not range_len_l else max(range_len_l)
            init_len  = 0 if not init_len_l  else max(init_len_l )
            if init_len>0:
                init_len += 4
            all_range = [x[2] for x in decl if 'range' in x[2]]
            has_range = len(all_range)>0
            if has_range:
                range_len +=1

            name_len  = max(name_len , self.cfg["align_entity.min_name_len" ])
            type_len  = max(type_len , self.cfg["align_entity.min_type_len" ])
            range_len = max(range_len, self.cfg["align_entity.min_range_len"])
            init_len  = max(init_len , self.cfg["align_entity.min_init_len" ])
            
            name_len  = min(name_len , self.cfg["align_entity.max_name_len" ])
            type_len  = min(type_len , self.cfg["align_entity.max_type_len" ])
            range_len = min(range_len, self.cfg["align_entity.max_range_len"])
            init_len  = min(init_len , self.cfg["align_entity.max_init_len" ])
            
            #print(decl)
            #print('Length params: N={} T={} R={} I={}'.format(name_len,type_len,range_len,init_len))
            comment_pos = name_len + 1 + type_len + range_len + init_len

            # Add params with alignement and copy non params line as is
            txt_new += '{}generic (\n'.format('\t'*(ilvl+1))
            for l in m.group('generic').strip().splitlines() :
                mp = re.match(re_params,l)
                if mp :
                    txt_new += '{ident}{name:<{length}} : '.format(ident='\t'*(ilvl+2),name=mp.group('name'),length=name_len)
                    txt_new += '{type:<{length}}'.format(type=mp.group('type'),length=type_len)
                    if range_len>0 :
                        if mp.group('range') :
                            if 'range' in mp.group('range'):
                                txt_new += ' '
                            txt_new += '{range:<{length}}'.format(range=mp.group('range'),length=range_len-1)
                        else :
                            txt_new += ' '*(range_len)
                    if init_len>0 :
                        if mp.group('init') :
                            txt_new += ' := {init:<{length}}'.format(init=mp.group('init'),length=init_len-4)
                        else :
                            txt_new += ' '*(init_len)
                    txt_new += ';' if mp.group('end') else ' '
                    if mp.group('comment'):
                        txt_new += ' -- {}'.format(mp.group('comment').strip())
                else :
                    mc = re.match(self.s_comment,l)
                    if mc :
                        pos = comment_pos if self.getIndentLevel(mc.group('space')) > (ilvl+2) else ilvl+2
                        txt_new += '{}{}'.format('\t'*comment_pos,mc.group(0).strip())
                    else :
                        # print('No match for "{}"'.format(l))
                        txt_new += l
                txt_new += '\n'
            txt_new += '{});\n'.format('\t'*(ilvl+1))

        if m.group('port') :
            # Extract all ports info to know width of each for future alignement
            ports = vhdl_util.clean_comment(m.group('port'))
            #print(ports)
            re_ports = r'''(?six)^[\ \t]*
                (?P<name>'''+self.s_id_list+r''')[\ \t]*:[\ \t]*
                (?P<dir>in|out|inout)[\ \t]+
                (?P<type>\w+)[\ \t]*
                (?P<range>\(.+?\))?
                (?P<init>[\ \t]*\:=[\ \t]*(?P<init_val>[^;]+?))?
                [\ \t]*(?P<end>;)?[\ \t]*(?:--(?P<comment>[^\n]*?))?$'''
            decl = re.findall(re_ports, ports ,flags=re.MULTILINE)
            # print(decl)
            name_len_l  = [] if not decl else [len(x[0].strip()) for x in decl]
            dir_len_l   = [] if not decl else [len(x[1].strip()) for x in decl]
            type_len_l  = [] if not decl else [len(x[2].strip()) for x in decl]
            range_len_l = [] if not decl else [len(x[3].strip()) for x in decl]
            init_len_l  = [] if not decl else [len(x[5].strip()) for x in decl]
            name_len  = 0 if not name_len_l   else max(name_len_l )
            dir_len   = 0 if not dir_len_l    else max(dir_len_l  )
            type_len  = 0 if not type_len_l   else max(type_len_l )
            range_len = 0 if not range_len_l  else max(range_len_l)
            init_len  = 0 if not init_len_l   else max(init_len_l )
            if init_len>0:
                init_len += 4
            all_range = [x[3] for x in decl if 'range' in x[3]]
            has_range = len(all_range)>0
            if has_range:
                range_len +=1

            name_len  = max(name_len , self.cfg["align_entity.min_name_len" ])
            type_len  = max(type_len , self.cfg["align_entity.min_type_len" ])
            range_len = max(range_len, self.cfg["align_entity.min_range_len"])
            init_len  = max(init_len , self.cfg["align_entity.min_init_len" ])

            # comment_pos = name_len + type_len + range_len + init_len + dir_len+6
            comment_pos = name_len + type_len + range_len + init_len + dir_len
            # print('Length ports: Nane={} Dir={} Type={} Range={} Init={} => {}'.format(name_len,dir_len,type_len,range_len,init_len,comment_pos))

            # Add params with alignement and copy non params line as is
            txt_new += '{}port (\n'.format('\t'*(ilvl+1))
            for l in m.group('port').strip().splitlines() :
                mp = re.match(re_ports,l)
                if mp :
                    txt_new += '{ident}{name:<{length}} : '.format(ident='\t'*(ilvl+2),name=mp.group('name'),length=name_len)
                    txt_new += '{dir:<{length}} '.format(dir=mp.group('dir'),length=dir_len)
                    txt_new += '{type:<{length}}'.format(type=mp.group('type'),length=type_len)
                    if range_len>0 :
                        if mp.group('range') :
                            if 'range' in mp.group('range'):
                                txt_new += ' {range:<{length}}'.format(range=mp.group('range'),length=range_len-1)
                            else :
                                txt_new += '{range:<{length}}'.format(range=mp.group('range'),length=range_len)
                        else :
                            txt_new += ' '*(range_len)
                    if init_len>0:
                        if mp.group('init_val') :
                            txt_new += ' := {val:<{length}}'.format(val=mp.group('init_val'),length=init_len-4)
                        else :
                            txt_new += ' '*init_len
                    txt_new += ';' if mp.group('end') else ' '
                    if mp.group('comment'):
                        txt_new += ' --{}'.format(mp.group('comment').rstrip())
                else :
                    mc = re.match(self.s_comment,l)
                    if mc :
                        txt_new += '\t'*(ilvl+2)
                        pos = comment_pos if self.getIndentLevel(mc.group('space')) > (ilvl+2) else 0
                        txt_new += '{}{}'.format(' '*pos,mc.group(0).strip())
                    else :
                        #print('No port match for "{}"'.format(l))
                        txt_new += l
                txt_new += '\n'
            txt_new += '{});\n'.format('\t'*(ilvl+1))
        txt_new += '{}{};'.format('\t'*ilvl, ' '.join(m.group('ending').split()) )

        #print(txt_new)
        return txt_new


    def alignInstance(self,txt,ilvl):
        m = re.match(r'(?si)(?P<emptyline>\n*)[ \t]*(?P<inst_name>\w+)\s*:\s*(?P<type>(?:component\s+|entity\s+\w+\.)?\w+\b(?:\([\w\s]+\))?)\s*(?:(?P<gen_or_port>generic|port)\s+map)\s*\((?P<content>.*)\)\s*;',txt)
        if not m:
            print('Fail')
            return ''
        txt_new = m.group('emptyline') + '\t'*(ilvl)
        txt_new += '{} : {}\n'.format(m.group('inst_name').strip(),m.group('type').strip())
        port_content = m.group('content')
        # Extract generic map part if it exist and provide alignment
        if m.group('gen_or_port').lower()=='generic' :
            m_content = re.match(r'(?si)(?P<gen_content>.*)\bport\s+map\s*\((?P<port_content>.*)',port_content)
            if not m_content:
                return ''
            gen_content = m_content.group('gen_content')
            # create a temporary string with no comment and find last closing parenthesis
            s_tmp = re.sub(r'--.*$',lambda m : ' '*len(m.group()) ,gen_content, flags=re.MULTILINE)
            pos_end = s_tmp[::-1].index(')')
            sep_content = gen_content[len(gen_content)-pos_end:].strip()
            gen_content = gen_content[:-pos_end-1].strip()
            txt_new += '\t'*(ilvl+1) + 'generic map (\n'
            txt_new += self.alignInstanceBinding(gen_content,ilvl+2)
            txt_new += '\t'*(ilvl+1) + ')\n'
            if sep_content:
                txt_new += '\t'*(ilvl+1) + sep_content + '\n'
            port_content = m_content.group('port_content')
        # Align port map
        txt_new += '\t'*(ilvl+1) + 'port map (\n'
        txt_new += self.alignInstanceBinding(port_content,ilvl+2)
        txt_new += '\t'*(ilvl+1) + ');'
        return txt_new

    def alignInstanceBinding(self,txt,ilvl):
        # ensure one bind per line
        # JAL: This screws up valid instance bindings with a comma on the RHS, so take it out.
        #      Instead, recommend checking for multiple '=>' tokens and skipping the line if 
        #      deemed invalid (this is not implemented!).
        # txt = re.sub(r',[ \t]*(\w+)',r',\n\1',txt.strip())

        txt = txt.strip()
        
        # re_bind = r'^\s*(?P<port>\w+(?:\s*\(./?\))?)\s*=>(?P<bind>.*?)(?P<sep>,?)\s*(?P<comment>[ \t]*--.*)?$'
        re_bind = r'''
            (?six)
            ^
            \s*
            (?P<port>\w+(\(.+?\))?)
            \s*=>\s*
            (?P<bind>\S*?\s*?(\(.+?\))?)\s*
            (?P<sep>,)?\s*
            (?P<comment>\s*--.*)?
            $
        '''

        port_len = self.cfg["align_inst.min_port_len"]
        bind_len = self.cfg["align_inst.min_bind_len"]

        for l in txt.splitlines() :
            m = re.match(re_bind,l)
            if m :
                port_len = max(port_len, len(m.group('port')))
                bind_len = max(bind_len, len(m.group('bind')))

        port_len = min(port_len, self.cfg["align_inst.max_port_len"])
        bind_len = min(bind_len, self.cfg["align_inst.max_bind_len"])
        
        # print('[alignInstanceBinding] : Max length port = {} , bind = {}'.format(port_len,bind_len))
        txt_new = ''
        for l in txt.splitlines() :
            # check if match binding
            m = re.match(re_bind,l)

            # Add indent level
            txt_new += '\t'*ilvl
            # in case of binding align port and signal together
            if m :
                # print("Matched line: " + l)
                # print("  port: '" + m.group('port') + "'")
                # print("  bind: '" + m.group('bind') + "'")
                # print("  sep: '" + m.group('sep') + "'")
                # print("  comment: '" + m.group('comment') + "'")
                txt_new += m.group('port').strip().ljust(port_len)
                txt_new += '\t=> '
                txt_new += m.group('bind').strip().ljust(bind_len)
                if m.group('sep'):
                    txt_new += ','
                else:
                    txt_new += ' '
                if m.group('comment'):
                    txt_new += ' ' + m.group('comment').strip()
            # No Binding ? copy line with indent level
            else :
                # print("No match: " + l.strip())
                txt_new += l.strip()
            txt_new += '\n'

        return txt_new

    def alignRecord(self,txt,ilvl):
        # TODO: Extract comment location to be sure to handle all case of strange comment location
        m = re.search(r"""(?six)^[\ \t]*type\s+
            (?P<name>\w+)\s+is\s+record
            (?P<content>.*?)
            end\s+record\s*;
            """, txt, re.MULTILINE)
        if m is None:
            return txt
        content = vhdl_util.clean_comment(m.group('content'))
        # print(content)
        re_field = r'''(?six)^[\ \t]*
                (?P<name>\w+)[\ \t]*:[\ \t]*
                (?P<type>[^;]+?);
                (?:[\ \t]*--(?P<comment>[^\n]*))?'''
        field = re.findall(re_field, content ,flags=re.MULTILINE)
        # print(field)
        name_len_l  = [] if not field else [len(x[0].strip()) for x in field]
        type_len_l  = [] if not field else [len(x[1].strip()) for x in field]
        name_len  = 0 if not name_len_l   else max(name_len_l )
        type_len  = 0 if not type_len_l   else max(type_len_l )

        comment_pos = name_len + type_len

        txt_new = '{}type {} is record\n'.format('\t'*(ilvl),m.group('name'))
        for l in m.group('content').strip().splitlines() :
            mf = re.match(re_field,l)
            if mf :
                txt_new += '{ident}{name:<{length}} : '.format(ident='\t'*(ilvl+1),name=mf.group('name'),length=name_len)
                txt_new += '{type:<{length}}'.format(type=mf.group('type'),length=type_len)
                txt_new += ';'
                if mf.group('comment'):
                    txt_new += ' --{}'.format(mf.group('comment').rstrip())
            else :
                mc = re.match(self.s_comment,l)
                if mc :
                    txt_new += '\t'*(ilvl+1)
                    pos = comment_pos if self.getIndentLevel(mc.group('space')) > (ilvl+1) else 0
                    txt_new += '{}{}'.format(' '*pos,mc.group(0).strip())
                else :
                    txt_new += l
            txt_new += '\n'
        txt_new += '{}end record;'.format('\t'*(ilvl))
        return txt_new

    def alignDecl(self,txt,ilvl):
        re_decl = r'''
            (?six)^[\ \t]*
            (?P<qual>\w+)[\ \t]*(?P<name>'''+self.s_id_list+r''')[\ \t]*:[\ \t]*
            (?P<type>\w+)[\ \t]*
            (?P<range>\(.+?\))?
            (?P<init>[\ \t]*\:=[\ \t]*(?P<init_val>[^;]+?))?
            [\ \t]*;[\ \t]*(?:--(?P<comment>[^\n]*))?$      
        '''

        decl = re.findall(re_decl, txt ,flags=re.MULTILINE)
        #print(decl)
        qual_len_l  = [] if not decl else [len(x[0].strip()) for x in decl]
        name_len_l  = [] if not decl else [len(x[1].strip()) for x in decl]
        type_len_l  = [] if not decl else [len(x[2].strip()) for x in decl]
        range_len_l = [] if not decl else [len(x[3].strip()) for x in decl]
        init_len_l  = [] if not decl else [len(x[5].strip()) for x in decl]
        qual_len  = 0 if not qual_len_l   else max(qual_len_l )
        name_len  = 0 if not name_len_l   else max(name_len_l )
        type_len  = 0 if not type_len_l   else max(type_len_l )
        range_len = 0 if not range_len_l  else max(range_len_l)
        init_len  = 0 if not init_len_l   else max(init_len_l )
        if init_len>0:
            init_len += 4

        qual_len  = max(qual_len,   self.cfg["align_decl.min_qual_len"]  ) 
        name_len  = max(name_len,   self.cfg["align_decl.min_name_len"]  )
        type_len  = max(type_len,   self.cfg["align_decl.min_type_len"]  )
        range_len = max(range_len,  self.cfg["align_decl.min_range_len"]  )
        init_len  = max(init_len,   self.cfg["align_decl.min_init_len"]  )
        
        #print('Len: qual = {}, name = {}, type = {}, range = {}, init = {} ({})'.format(qual_len,name_len,type_len,range_len,init_len,init_len))
        
        txt_new = ''
        for l in txt.strip().splitlines() :
            mp = re.match(re_decl,l)
            if mp :
                txt_new += '{ident}{qual:<{length}} '.format(ident='\t'*ilvl,qual=mp.group('qual'),length=qual_len)
                txt_new += '{name:<{length}} : '.format(name=mp.group('name').strip(),length=name_len)
                txt_new += '{type:<{length}}'.format(type=mp.group('type'),length=type_len)
                if range_len>0 :
                    if mp.group('range') :
                        if 'range' in mp.group('range'):
                            txt_new += ' {range:<{length}}'.format(range=mp.group('range'),length=range_len-1)
                        else :
                            txt_new += '{range:<{length}}'.format(range=mp.group('range'),length=range_len)
                    else :
                        txt_new += ' '*(range_len)
                if init_len>0:
                    if mp.group('init_val') :
                        txt_new += ' := {val:<{length}}'.format(val=mp.group('init_val'),length=init_len-4)
                    else :
                        txt_new += ' '*init_len
                txt_new += ';'
                if mp.group('comment'):
                    txt_new += ' --{}'.format(mp.group('comment').rstrip())
            else :
                txt_new += l
            txt_new += '\n'

        #print(txt_new)
        return txt_new[:-1]


    def setKeywordCase(self, txt):
        re_decl = r'''(?six)
                ^
                (?P<non_comment>.*?)
                (?P<comment>--.*)?
                $
            '''

        # VHDL keywords
        re_keyword = r'''
                (?six)
                (?<=[^a-z0-9_'])
                (?P<keyword>
                    signal|port|generic|map|downto|to|range|in|out|entity|architecture|type|subtype|is|array|of
                )
                (?=[^a-z0-9_])
            '''
            
        # IEEE standard types/functions
        re_ieee = r'''
                (?six)
                (?<=[^a-z0-9_'])
                (?P<keyword>
                    std_logic|std_logic_vector|bit|bit_vector|unsigned|signed|natural|shift_left|resize
                )
                (?=[^a-z0-9_])
            '''

        # VHDL attributes
        re_attribute = r'''
                (?six)
                (?P<keyword>
                    'ascending|'base|'delayed|'driving|'driving_value|'event|'high|'image|'instance_name|'last_active|'last_event|'last_value|'left|'leftof|'length|'low|'path_name|'pos|'pred|'quiet|'range|'reverse_range|'right|'rightof|'simple_name|'stable|'succ|'transaction|'val|'value
                )
                (?=[^a-z0-9_])
            '''
            
        txt_new = ''
        for l in txt.splitlines() :
            mp = re.match(re_decl,l)
            if mp :
                
                tmp = mp.group('non_comment')
                
                if self.cfg['upper_case_keywords']:
                    tmp = re.sub(re_keyword, lambda match: r'{}'.format(match.group('keyword').upper()), tmp)
                else:
                    tmp = re.sub(re_keyword, lambda match: r'{}'.format(match.group('keyword').lower()), tmp)
                    
                if self.cfg['upper_case_ieee']:
                    tmp = re.sub(re_ieee, lambda match: r'{}'.format(match.group('keyword').upper()), tmp)
                else:
                    tmp = re.sub(re_ieee, lambda match: r'{}'.format(match.group('keyword').lower()), tmp)
                    
                if self.cfg['upper_case_attributes']:
                    tmp = re.sub(re_attribute, lambda match: r'{}'.format(match.group('keyword').upper()), tmp)
                else:
                    tmp = re.sub(re_attribute, lambda match: r'{}'.format(match.group('keyword').lower()), tmp)

                txt_new += tmp
                    
                if mp.group('comment'):
                    txt_new += mp.group('comment')
                    
                    
            else:
                txt_new += l
                
            txt_new += '\n'
        
        return txt_new[:-1]
            
