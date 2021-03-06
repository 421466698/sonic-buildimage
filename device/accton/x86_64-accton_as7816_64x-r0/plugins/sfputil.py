#!/usr/bin/env python

try:
    import time
    import string
    from ctypes import create_string_buffer
    from sonic_sfp.sfputilbase import SfpUtilBase 
except ImportError, e:
    raise ImportError (str(e) + "- required module not found")

#from xcvrd
SFP_STATUS_INSERTED = '1'
SFP_STATUS_REMOVED = '0'

class SfpUtil(SfpUtilBase):
    """Platform specific SfpUtill class"""

    _port_start = 1
    _port_end = 64
    ports_in_block = 64

    _port_to_eeprom_mapping = {}
    port_to_i2c_mapping = {
        61 : 25,
        62 : 26,
        63 : 27,
        64 : 28,
        55 : 29,
        56 : 30,
        53 : 31,
        54 : 32,
        9  : 33,
        10 : 34,
        11 : 35,
        12 : 36,
        1  : 37,
        2  : 38,
        3  : 39,
        4  : 40,
        6  : 41,
        5  : 42,
        8  : 43,
        7  : 44,
        13 : 45,
        14 : 46,
        15 : 47,
        16 : 48,
        17 : 49,
        18 : 50,
        19 : 51,
        20 : 52,
        25 : 53,
        26 : 54,
        27 : 55,
        28 : 56,
        29 : 57,
        30 : 58,
        31 : 59,
        32 : 60,
        21 : 61,
        22 : 62,
        23 : 63,
        24 : 64,
        41 : 65,
        42 : 66,
        43 : 67,
        44 : 68,
        33 : 69,
        34 : 70,
        35 : 71,
        36 : 72,
        45 : 73,
        46 : 74,
        47 : 75,
        48 : 76,
        37 : 77,
        38 : 78,
        39 : 79,
        40 : 80,
        57 : 81,
        58 : 82,
        59 : 83,
        60 : 84,
        49 : 85,
        50 : 86,
        51 : 87,
        52 : 88,}

    _qsfp_ports = range(0, ports_in_block + 1)

    def __init__(self):
        eeprom_path = '/sys/bus/i2c/devices/{0}-0050/eeprom'
        for x in range(self.port_start, self.port_end + 1):
            port_eeprom_path = eeprom_path.format(self.port_to_i2c_mapping[x])
            self._port_to_eeprom_mapping[x] = port_eeprom_path
        SfpUtilBase.__init__(self)

    def reset(self, port_num):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False
	path = "/sys/bus/i2c/devices/19-0060/module_reset_{0}"
        port_ps = path.format(port_num)
          
        try:
            reg_file = open(port_ps, 'w')
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False

        #HW will clear reset after set.
        reg_file.seek(0)
        reg_file.write('1')
        reg_file.close()
        return True
        
    def get_presence(self, port_num):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

        path = "/sys/bus/i2c/devices/19-0060/module_present_{0}"
        port_ps = path.format(port_num)
          
        try:
            reg_file = open(port_ps)
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False

        reg_value = reg_file.readline().rstrip()
        if reg_value == '1':
            return True

        return False

    @property
    def port_start(self):
        return self._port_start

    @property
    def port_end(self):
        return self._port_end
	
    @property
    def qsfp_ports(self):
        return range(0, self.ports_in_block + 1)

    @property 
    def port_to_eeprom_mapping(self):
         return self._port_to_eeprom_mapping

    def get_low_power_mode(self, port_num):
        # Check for invalid port_num
        if port_num < self._port_start or port_num > self._port_end:
            return False

        try:
            eeprom = None

            if not self.get_presence(port_num):
                return False

            eeprom = open(self.port_to_eeprom_mapping[port_num], "rb")
            eeprom.seek(93)
            lpmode = ord(eeprom.read(1))

            if ((lpmode & 0x3) == 0x3):
                return True # Low Power Mode if "Power override" bit is 1 and "Power set" bit is 1
            else:
                return False # High Power Mode if one of the following conditions is matched:
                             # 1. "Power override" bit is 0
                             # 2. "Power override" bit is 1 and "Power set" bit is 0 
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False
        finally:
            if eeprom is not None:
                eeprom.close()
                time.sleep(0.01)

    def set_low_power_mode(self, port_num, lpmode): 
        # Check for invalid port_num
        if port_num < self._port_start or port_num > self._port_end:
            return False

        try:
            eeprom = None

            if not self.get_presence(port_num):
                return False # Port is not present, unable to set the eeprom

            # Fill in write buffer
            regval = 0x3 if lpmode else 0x1 # 0x3:Low Power Mode, 0x1:High Power Mode
            buffer = create_string_buffer(1)
            buffer[0] = chr(regval)

            # Write to eeprom
            eeprom = open(self.port_to_eeprom_mapping[port_num], "r+b")
            eeprom.seek(93)
            eeprom.write(buffer[0])
            return True
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)
            return False
        finally:
            if eeprom is not None:
                eeprom.close()
                time.sleep(0.01)

    @property
    def _get_present_bitmap(self):
        nodes = []

        cpld_path = "/sys/bus/i2c/devices/19-0060/"
        nodes.append(cpld_path + "module_present_all")

        bitmap = ""
        for node in nodes:
            try:
                reg_file = open(node)

            except IOError as e:
                print "Error: unable to open file: %s" % str(e)
                return False
            bitmap += reg_file.readline().rstrip() + " "
            reg_file.close()

        rev = bitmap.split(" ")
        rev = "".join(rev[::-1])
        return int(rev,16)


    data = {'valid':0, 'last':0, 'present':0}
    def get_transceiver_change_event(self, timeout=2000):
        now = time.time()
        port_dict = {}
        port = 0

        if timeout < 1000:
            timeout = 1000
        timeout = (timeout) / float(1000) # Convert to secs

        if now < (self.data['last'] + timeout) and self.data['valid']:
            return True, {}

        reg_value = self._get_present_bitmap
        reg_value = ~reg_value
        changed_ports = self.data['present'] ^ reg_value
        if changed_ports:
            for port in range (self.port_start, self.port_end+1):
                # Mask off the bit corresponding to our port
                mask = (1 << (port - 1))
                if changed_ports & mask:
                    if (reg_value & mask) == 0:
                        port_dict[port] = SFP_STATUS_REMOVED
                    else:
                        port_dict[port] = SFP_STATUS_INSERTED

            # Update cache
            self.data['present'] = reg_value
            self.data['last'] = now
            self.data['valid'] = 1
            return True, port_dict
        else:
            return True, {}
        return False, {}

