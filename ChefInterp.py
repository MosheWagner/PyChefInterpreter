import sys
import re
import random
import copy
import datetime

start = datetime.datetime.now()


def bowl_idx(bowl_str):
    try:
        return int(bowl_str.strip())-1
    except ValueError:
        return int(bowl_str.strip()[:-2])-1


class Chef:
    def __init__(self, script, mixingbowls={0: []}):
        self.script = script
        self.origscript = script
        self.mixingbowls = copy.deepcopy(mixingbowls)
        self.bakingdishes = {}

    def parse(self):
        self.recipename = re.match("(.*?)\.\n\n", self.script)
        self.script = re.sub(self.recipename.group(), "", self.script)
        if (self.recipename == None):
            print "Invalid recipe name"
            sys.exit(-1)
        # Match a recipe name, first line of script, must end with a dot and two newlines.
        # Replace this with nothing to allow for further matching.
        self.comment = re.match("(.*?)\n\n", self.script, re.DOTALL)
        # Find a comment, and replace it.
        if self.comment != None and re.match("^Ingredients", self.comment.group()) == None:
            # Make sure we do not replace the ingredient list.
            self.script = re.sub(re.escape(self.comment.group()), "", self.script)
            # Replace the comment with nothing.
        self.ingr = re.match("Ingredients\.\n", self.script)
        # Find ingredient list.
        if self.ingr == None:
            print "Ingredient list not found"
            sys.exit(-1)
        self.script = re.sub(self.ingr.group(), "", self.script, 1)
        # Again, replace with nothing.
        self.ingredients = re.findall(
            "(([0-9]*) ?(k?g|pinch(?:es)?|m?l|dash(?:es)?|cups?|teaspoons?|tablespoons?)? ?([a-zA-Z ]+)\n)",
            self.script)
        # Match ingredients.
        self.ingredientlist = {}
        for i in self.ingredients:
            if re.match(i[0], self.script) != None:
                # Replace them with nothing, but only if they are exactly at the beginning of the script
                # to avoid replacing axuiliary ingredients.
                self.script = self.script.replace(i[0], "")
                # Type assignment is next. Note that chr() is not run on values until output. This is to allow arithmetic operations on liquids.
            if (i[2] in ("dash", "cup", "l", "ml", "dashes", "cups")):
                value = int(i[1])
                type = "liquid"
            else:
                try:
                    value = int(i[1])
                except ValueError:
                    value = None
                type = "dry"
            self.ingredientlist[i[3]] = [value, type, i[3]]
        # Find the method. This is where things get intresting.
        self.script = self.script.lstrip()
        self.meth = re.match("Method\.\n", self.script)
        self.script = re.sub(self.meth.group(), "", self.script, 1)
        self.method = re.match("(.*?)\n\n", self.script, re.DOTALL)
        # Match anything up to two newlines.
        self.execute(self.method.group(1))
        # Run the script^H^H^H^H^H^H^H^H^H^H^H^H^HCook the food.
        serves = re.search("Serves ([0-9]+).", self.script)
        # Find output directive.
        if serves != None:
            output = self.serve(int(serves.group(1)))
            # Call function to return output
            return output

    def ambigcheck(self, text, dish=False):
        # A mixing bowl may not be used without a number if other mixing bowls use numbers. Same goes for baking dishes.
        if re.match("the (1st|2nd|3rd|[0-9]+th) mixing bowl", text) != None:
            print "Ambigious mixing bowl"
            sys.exit(-1)
        if dish == True:
            if re.match("the (1st|2nd|3rd|[0-9]+th) baking dish", text) != None:
                print "Ambigious baking dish"
                sys.exit(-1)

    def valuecheck(self, ingredient):
        # Ingredients may be defined without a value, but not used without one.
        if self.ingredientlist[ingredient][0] == None:
            print "Cooking time error: tried to access ingredient", ingredient + ", which is not ready for use."
            sys.exit()

    def put(self, mixingbowl, value):
        # Add an ingredient to a mixing bowl.
        if mixingbowl == None:
            if len(self.mixingbowls) > 0:
                self.mixingbowls[0].append(value)
            else:
                self.mixingbowls[0] = []
                self.mixingbowls[0].append(value)
        else:
            key = bowl_idx(mixingbowl)
            if key not in self.mixingbowls:
                self.mixingbowls[key] = []
            self.mixingbowls[key].append(value)
            # Numbered mixing bowls use their number - 1 as index.

    def fold(self, ingredient, mixingbowl):
        # Opposite of put.
        if 'apple' in ingredient:
            pass

        if mixingbowl == None:
            key = 0
        else:
            key = bowl_idx(mixingbowl)
        self.ingredientlist[ingredient] = self.mixingbowls[key].pop()

    def addingredient(self, ingredient, mixingbowl):
        value = self.ingredientlist[ingredient][0]
        if mixingbowl == None:
            key = 0
        else:
            key = bowl_idx(mixingbowl)
        # Add values
        self.mixingbowls[key][-1][0] += value

    def removeingredient(self, ingredient, mixingbowl):
        # Subtraction
        value = self.ingredientlist[ingredient][0]
        if mixingbowl == None:
            key = 0
        else:
            key = bowl_idx(mixingbowl)
        self.mixingbowls[key][-1][0] -= value

    def combineingredient(self, ingredient, mixingbowl):
        # Multiplication
        value = self.ingredientlist[ingredient][0]
        if mixingbowl == None:
            key = 0
        else:
            key = bowl_idx(mixingbowl)
        self.mixingbowls[key][-1][0] *= value

    def stir(self, ingredient, mixingbowl):
        # Multiplication
        value = self.ingredientlist[ingredient][0]
        if mixingbowl == None:
            key = 0
        else:
            key = bowl_idx(mixingbowl)

        if value >= len(self.mixingbowls[key]):
            value = len(self.mixingbowls[key])

        self.mixingbowls[key] = self.mixingbowls[key][0:-value-1] + [self.mixingbowls[key][-1]] + self.mixingbowls[key][-value-1:-1]

    def divideingredient(self, ingredient, mixingbowl):
        # Division
        value = self.ingredientlist[ingredient][0]
        if mixingbowl == None:
            key = 0
        else:
            key = bowl_idx(mixingbowl)
        self.mixingbowls[key][-1][0] /= value

    def execute(self, text, loop=False):
        # Main interpreting function.
        excode = re.split("\.\s+", text)

        # Split into sentences.
        def stripwhite(x):
            return x.lstrip()

        excode = map(stripwhite, excode)
        excode[-1] = excode[-1][:-1]
        for ex in excode:
            # print ex, self.mixingbowls[0] # , self.ingredientlist
            # Do a series of regexps, call appropriate function.
            put = re.search("^Put ?([a-zA-Z ]+) into (?:the )?(?:([1-9]\d*)(?:st|nd|rd|th) )?mixing bowl", ex)
            if put != None:
                if put.group(2) == None:
                    self.ambigcheck(text)
                self.put(put.group(2), copy.copy(self.ingredientlist[put.group(1)]))
            fold = re.search("Fold ([a-zA-Z ]+) into (?:the )?(?:(1st|2nd|3rd|[0-9]+th) )?mixing bowl", ex)
            if fold != None:
                if fold.group(2) == None:
                    self.ambigcheck(text)
                self.fold(fold.group(1), fold.group(2))
            add = re.search("Add ([a-zA-Z ]+?) to (?:the )?(?:(1st|2nd|3rd|[0-9]+th) )?mixing bowl", ex)
            if add != None:
                if add.group(2) == None:
                    self.ambigcheck(text)
                self.addingredient(add.group(1), add.group(2))
            remove = re.search("Remove ([a-zA-Z ]+?) from (?:the )?(?:(1st|2nd|3rd|[0-9]+th) )?mixing bowl", ex)
            if remove != None:
                if remove.group(2) == None:
                    self.ambigcheck(text)
                self.removeingredient(remove.group(1), remove.group(2))
            combine = re.search("Combine ([a-zA-Z ]+?) into (?:the )?(?:(1st|2nd|3rd|[0-9]+th) )?mixing bowl", ex)
            if combine != None:
                if combine.group(2) == None:
                    self.ambigcheck(text)
                self.combineingredient(combine.group(1), combine.group(2))
            stir = re.search("Stir ([a-zA-Z ]+?) into (?:the )?(?:(1st|2nd|3rd|[0-9]+th) )?mixing bowl", ex)
            if stir != None:
                if stir.group(2) == None:
                    self.ambigcheck(text)
                self.stir(stir.group(1), stir.group(2))
            divide = re.search("Divide ([a-zA-Z ]+?) to (?:the )?(?:(1st|2nd|3rd|[0-9]+th) )?mixing bowl", ex)
            if divide != None:
                if divide.group(2) == None:
                    self.ambigcheck(text)
                self.divideingredient(divide.group(1), divide.group(2))
            liquefy = re.search("Liquefy contents of the (1st|2nd|3rd|[0-9]+th)? ?mixing bowl", ex)
            if liquefy != None:
                if liquefy.group(1) == None:
                    self.ambigcheck(text)
                    for i in self.mixingbowls[0]:
                        if (i[1] == "dry"):
                            i[1] = "liquid"
                continue
            liquefy2 = re.search("Liquefy [a-zA-Z]", ex)
            if liquefy != None:
                self.ingredientlist[liquefy.group(1)]
                continue
            clean = re.search("Clean the (1st|2nd|3rd|[0-9]+th)? ?mixing bowl", ex)
            if clean != None:
                if clean.group(1) == None:
                    self.mixingbowls[0] = []
                else:
                    if self.mixingbowls.has_key(clean.group(1)[:-2]):
                        self.mixingbowls[clean.group(1)[:-2]] = []
                    else:
                        existslater = re.match(clean.group(1) + " mixing bowl", text)
                        if existslater == None:
                            print "Warning: Unknown mixingbowl", clean.group(1)
                        else:
                            print "Warning: Tried to clean mixingbowl", clean.group(1), "before putting anything in it!"
                continue
            mix = re.search("Mix the (1st|2nd|3rd|[0-9]+th)? ?mixing bowl well", ex)
            if mix != None:
                if mix.group(1) == None:
                    random.shuffle(self.mixingbowls[0])
                else:
                    if self.mixingbowls.has_key(mix.group(1)[:-2]):
                        random.shuffle(self.mixingbowls[clean.mix(1)[:-2]])
                    else:
                        existslater = re.match(clean.mix(1) + " mixing bowl", text)
                        if existslater == None:
                            print "Warning: Unknown mixing bowl", mix.group(1)
                        else:
                            print "Warning: Tried to mix mixing bowl", mix.group(1), "before putting anything in it!"
                continue
            fridge = re.search("Take ([a-zA-Z]+) from refrigerator", ex)
            if (fridge != None):
                if self.ingredientlist.has_key(fridge.group(1)):
                    value = int(raw_input(fridge.group(1) + ": "))
                    if self.ingredientlist[fridge.group(1)][1] == "liquid":
                        self.ingredientlist[fridge.group(1)][0] = chr(value)
                    else:
                        self.ingredientlist[fridge.group(1)][0] = value
                continue
            pour = re.search(
                "Pour contents of the (?:the )?(?:([1-9]\d*)(?:st|nd|rd|th) )?mixing bowl into the (?:the )?(?:([1-9]\d*)(?:st|nd|rd|th) )?baking dish",
                ex)
            if pour != None:
                if pour.group(1) == None:
                    key = 0
                else:
                    key = int(pour.group(1)) - 1
                if pour.group(2) == None:
                    key2 = 0
                else:
                    key2 = int(pour.group(2)) - 1
                self.ambigcheck(text, True)
                if not self.bakingdishes.has_key(key2):
                    self.bakingdishes[key2] = []
                self.bakingdishes[key2].extend(self.mixingbowls[key])
                continue
            refer = re.search("Refrigerate (?:for ([0-9]+))? hours", ex)
            if refer != None:
                if refer.group(1) != None:
                    self.serve(refer.group(1))
                sys.exit()
            adddry = re.search("Add dry ingredients(?: to the (1st|2nd|3rd|[0-9]+th) mixing bowl)?", ex)
            if adddry != None:
                def isdry(x):
                    return x[1] == "dry"

                def dryvalues(x):
                    return x[0]

                dry = filter(isdry, self.ingredientlist.values())
                dry = map(dryvalues, dry)
                self.put(adddry.group(1), [sum(dry), "dry", "sumofall"], text)
            auxiliary = re.match("Serve with ([a-zA-Z ]+)", ex)
            if auxiliary != None:
                if 'XorRev' in auxiliary.group(1):
                    pass
                if 'Dec' in auxiliary.group(1):
                    pass

                auxtext = re.search(auxiliary.group(1) + "\.\n\n(.*)", self.origscript, re.IGNORECASE | re.DOTALL)
                souschef = Chef(auxtext.group(), copy.copy(self.mixingbowls))
                souschef.parse()
                readymixingbowls = souschef.mixingbowls
                self.mixingbowls[0].extend(readymixingbowls[0])
            verb = re.search("([a-zA-Z]+) the ([a-zA-Z ]+) ?(?!until)", ex)
            if verb != None:
                if "until" in verb.group():
                    continue
                if not self.ingredientlist.has_key(verb.group(2)):
                    continue
                if self.ingredientlist[verb.group(2)][0] == 0:
                    continue
                else:
                    if verb.group(1)[-1] == "e":
                        verbw = verb.group(1)[:-1]
                    elif verb.group(1)[-1] == "y":
                        verbw = verb.group(1)[:-1] + "i"
                    else:
                        verbw = verb.group(1)
                    looptext = re.search(
                        verb.group() + "\.((.*?)\s+[a-zA-Z]+ (?:the ([a-zA-Z ]+)) until " + verbw + "ed)", text,
                        re.DOTALL | re.IGNORECASE)
                    deltext = re.split("\.\s+", looptext.group(1))

                    for d in deltext:
                        excode.remove(d.strip())
                    while self.ingredientlist[verb.group(2)][0] != 0:
                        r = self.execute(looptext.group(2), True)
                        if r == "ENDOFLOOP":
                            break
                        if looptext.group(3) != None:
                            self.ingredientlist[looptext.group(3)][0] -= 1
            if loop == True:
                setaside = re.search("Set aside", ex)
                if setaside != None:
                    return "ENDOFLOOP"

    def serve(self, number):
        output = ""
        for i in range(0, number):
            self.bakingdishes[i].reverse()
            for j in self.bakingdishes[i]:
                value = j[0]
                if j[1] == "liquid":
                    value = chr(value)
                output += str(value)
        return output


if __name__ == "__main__":
    print "PyChef v0.0.1 by sp3tt. This program is licensed under the GNU GPL."
    print "Small bugs fixed by Moshewag and Yaakov1"
    try:
        f = open(sys.argv[1], "r")
    except IOError, text:
        print text
        sys.exit(-1)
    main = Chef(f.read())
    print main.parse()
    end = datetime.datetime.now()
