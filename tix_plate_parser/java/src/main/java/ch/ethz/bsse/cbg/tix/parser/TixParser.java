package ch.ethz.bsse.cbg.tix.parser;

import ch.ethz.bsse.cbg.tix.structs.CellFeature;
import ch.ethz.bsse.cbg.tix.structs.LibraryLayout;
import ch.ethz.bsse.cbg.tix.util.Files;

import java.io.File;
import java.util.List;

/**
 * @author Simon Dirmeier {@literal simon.dirmeier@gmx.de}
 */
public final class TixParser
{
    private final String _PLATE_FOLDER;
    private final String _META_FILE;
    private final LibraryLayout _LAYOUT;

    public TixParser(String plateFolder, String metaFile)
    {
        this._PLATE_FOLDER = plateFolder;
        this._META_FILE = metaFile;
        System.out.println("1");
        this._LAYOUT = null;
//        this._LAYOUT = LibraryLayout.instance(this._META_FILE);
//        System.out.println(this._LAYOUT.find("cb01-1a10a", "adeno", 1, "selleck", "a1"));
    }

    public final void parse()
    {
        System.out.println(2);
        List<File> fileList = Files.listFiles(new File(_PLATE_FOLDER));
        System.out.println(3);
        final int sz = fileList.size();
        System.out.println(4);
        CellFeature[] plateFeatures = new CellFeature[sz];
        System.out.println(5);
        for (int i = 0; i < sz; i++)
        {
            plateFeatures[i] = new CellFeature(fileList.get(i));
            System.exit(-1);
        }
    }
}